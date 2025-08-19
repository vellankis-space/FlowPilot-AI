import json
import os
import re
import time
from typing import Dict, List, Tuple

import requests
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from urllib.parse import urljoin, urlparse


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    retry = Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "HEAD"),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def _detect_table_headers(table_soup: Tag) -> List[str]:
    thead = table_soup.find("thead")
    if thead:
        ths = thead.find_all("th")
        if ths:
            return [_clean_text(th.get_text()) for th in ths]

    # Fallback: some tables omit thead; use first row's th/td as headers
    first_row = table_soup.find("tr")
    if first_row:
        cells = first_row.find_all(["th", "td"])
        if cells:
            return [_clean_text(c.get_text()) for c in cells]
    return []


def get_parameters(table_soup: Tag) -> List[Dict[str, str]]:
    rows_out: List[Dict[str, str]] = []
    headers = _detect_table_headers(table_soup)
    # Normalize headers
    normalized_headers: List[str] = []
    for header in headers:
        h = header.lower()
        if "argument" in h or "name" == h or "parameter" in h:
            normalized_headers.append("Name")
        elif "optional" in h:
            normalized_headers.append("Optional")
        elif "accepts" in h or "type" in h:
            normalized_headers.append("Type")
        elif "default" in h:
            normalized_headers.append("Default Value")
        elif "description" in h:
            normalized_headers.append("Description")
        elif "variable" in h or "output" in h:
            normalized_headers.append("Variable")
        elif "exception" in h or "error" in h:
            normalized_headers.append("Exception")
        else:
            normalized_headers.append(header)

    tbody = table_soup.find("tbody") or table_soup
    rows = tbody.find_all("tr") if tbody else []
    if rows and rows[0].find_all("th"):
        rows = rows[1:]

    for row in rows:
        cells = row.find_all("td")
        if not cells:
            continue
        cell_texts = [_clean_text(c.get_text()) for c in cells]
        detail: Dict[str, str] = {}
        for idx, value in enumerate(cell_texts):
            key = normalized_headers[idx] if idx < len(normalized_headers) else f"Col{idx+1}"
            detail[key] = value
        if detail:
            rows_out.append(detail)
    return rows_out


def _heading_level(tag: Tag) -> int:
    if not isinstance(tag, Tag):
        return 99
    if tag.name and tag.name.startswith("h") and len(tag.name) == 2 and tag.name[1].isdigit():
        return int(tag.name[1])
    return 99


def _first_paragraph_after(heading: Tag) -> str:
    tag = heading
    base_level = _heading_level(heading)
    while tag:
        tag = tag.find_next_sibling()
        if tag is None:
            break
        if isinstance(tag, Tag) and tag.name and tag.name.startswith("h") and _heading_level(tag) <= base_level:
            break
        if isinstance(tag, Tag) and tag.name == "p":
            text = _clean_text(tag.get_text())
            if text:
                return text
    return ""


def _collect_sectioned_tables(heading: Tag) -> List[Tuple[str, Tag]]:
    action_level = _heading_level(heading)
    sectioned: List[Tuple[str, Tag]] = []
    current_section: str = None
    tag = heading
    while tag:
        tag = tag.find_next_sibling()
        if tag is None:
            break
        if isinstance(tag, Tag) and tag.name and tag.name.startswith("h"):
            level = _heading_level(tag)
            if level <= action_level:
                break
            section_text = _clean_text(tag.get_text()).lower()
            if "input" in section_text and "parameter" in section_text:
                current_section = "Input parameters"
            elif ("variable" in section_text or "output" in section_text) and ("produced" in section_text or True):
                current_section = "Variables produced"
            elif "exception" in section_text or "error" in section_text:
                current_section = "Exceptions"
            else:
                current_section = None
            continue
        if isinstance(tag, Tag) and tag.name == "table":
            sectioned.append((current_section, tag))
        if isinstance(tag, Tag) and tag.name in ("section", "div"):
            for t in tag.find_all("table"):
                sectioned.append((current_section, t))
    return sectioned


def _map_input(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for r in rows:
        argument = r.get("Name") or r.get("Argument") or r.get("Parameter") or r.get("Col1")
        ptype = r.get("Type") or r.get("Accepts") or r.get("Col2")
        description = r.get("Description") or r.get("Col3")
        item: Dict[str, str] = {}
        if argument:
            item["Argument"] = argument
        if ptype:
            item["Type"] = ptype
        if description:
            item["Description"] = description
        if item:
            out.append(item)
    return out


def _map_output(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for r in rows:
        argument = r.get("Variable") or r.get("Name") or r.get("Output") or r.get("Col1")
        ptype = r.get("Type") or r.get("Accepts") or r.get("Col2")
        description = r.get("Description") or r.get("Col3")
        item: Dict[str, str] = {}
        if argument:
            item["Argument"] = argument
        if ptype:
            item["Type"] = ptype
        if description:
            item["Description"] = description
        if item:
            out.append(item)
    return out


def _map_exceptions(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for r in rows:
        ex = r.get("Exception") or r.get("Name") or r.get("Error") or r.get("Col1")
        description = r.get("Description") or r.get("Col2")
        item: Dict[str, str] = {}
        if ex:
            item["Exception"] = ex
        if description:
            item["Description"] = description
        if item:
            out.append(item)
    return out


def parse_page(session: requests.Session, url: str, category: str) -> List[Dict]:
    print(f"Scraping {url}...")
    resp = session.get(url, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")

    main = soup.find("main") or soup
    actions: List[Dict] = []

    # Heuristic: actions likely under h3/h4; collect both
    for heading in main.find_all(["h4", "h3", "h2"]):
        name = _clean_text(heading.get_text())
        if not name or len(name) < 2:
            continue
        lower = name.lower()
        # Skip generic sections
        if any(k in lower for k in [
            "table of contents",
            "feedback",
            "additional resources",
            "input parameters",
            "variables produced",
            "outputs",
            "exceptions",
            "errors",
        ]):
            continue

        description = _first_paragraph_after(heading) or "N/A"
        sectioned = _collect_sectioned_tables(heading)

        input_params: List[Dict[str, str]] = []
        outputs: List[Dict[str, str]] = []
        exceptions: List[Dict[str, str]] = []

        for section, table in sectioned:
            rows = get_parameters(table)
            if not rows:
                continue
            headers = _detect_table_headers(table)
            headers_joined = " ".join(h.lower() for h in headers)
            if section == "Exceptions" or "exception" in headers_joined or "error" in headers_joined:
                exceptions.extend(_map_exceptions(rows))
            elif section == "Variables produced" or "variable" in headers_joined or "output" in headers_joined:
                outputs.extend(_map_output(rows))
            else:
                input_params.extend(_map_input(rows))

        if not (input_params or outputs or exceptions):
            continue

        actions.append({
            "tool": "Automation Anywhere",
            "category": category,
            "action": name,
            "description": description,
            "Input parameters": input_params,
            "Variables produced": outputs,
            "Exceptions": exceptions,
        })
        time.sleep(0.2)

    return actions


def _project_path(*parts: str) -> str:
    base_dir = os.path.dirname(__file__)  # backend/
    return os.path.join(base_dir, *parts)


def main() -> None:
    links_path = _project_path("data", "automation_anywhere_action_links.json")
    out_path = _project_path("data", "automation_anywhere_actions_detailed.json")

    DEFAULT_INDEX_URL = (
        "https://docs.automationanywhere.com/bundle/enterprise-v2019/page/enterprise-cloud/topics/aae-client/bot-creator/using-the-workbench/cloud-commands-panel.html"
    )

    def _discover_links_from_index(session: requests.Session, index_url: str) -> List[Dict[str, str]]:
        print(f"Discovering package/action links from index: {index_url}")
        resp = session.get(index_url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")
        main = soup.find("main") or soup
        anchors = main.find_all("a")
        discovered: List[Dict[str, str]] = []
        seen: set = set()
        for a in anchors:
            text = _clean_text(a.get_text())
            href = a.get("href")
            if not href:
                continue
            full = urljoin(index_url, href)
            # Basic filters: same docs domain, not mailto, not fragment-only
            parsed = urlparse(full)
            if parsed.scheme not in ("http", "https"):
                continue
            if "docs.automationanywhere.com" not in parsed.netloc:
                continue
            if parsed.fragment and parsed.path == urlparse(index_url).path:
                # same page anchor
                continue
            # Heuristics for package/action pages
            lowered = (text or "").lower()
            if ("package" in lowered) or ("packages" in lowered) or ("actions" in lowered):
                key = (text, full)
                if key in seen:
                    continue
                seen.add(key)
                discovered.append({"action": text or "Unknown", "url": full})
        # De-duplicate by URL
        unique_by_url: Dict[str, Dict[str, str]] = {}
        for item in discovered:
            unique_by_url.setdefault(item["url"], item)
        return list(unique_by_url.values())

    session = _make_session()

    links: List[Dict[str, str]] = []
    if os.path.exists(links_path):
        with open(links_path, "r") as f:
            try:
                links = json.load(f)
            except Exception:
                links = []
    # If links are missing or very few, auto-discover from the index URL
    if not links or len(links) < 5:
        links = _discover_links_from_index(session, DEFAULT_INDEX_URL)
        if not links:
            print("No links discovered from index; aborting.")
            return
        os.makedirs(os.path.dirname(links_path), exist_ok=True)
        with open(links_path, "w") as f:
            json.dump(links, f, indent=2, ensure_ascii=False)
        print(f"Discovered and saved {len(links)} links to {links_path}")

    all_actions: List[Dict] = []

    for link in links:
        try:
            category = link.get("action", "Unknown")
            url = link["url"]
            all_actions.extend(parse_page(session, url, category))
            time.sleep(0.5)
        except Exception as e:
            print(f"Error scraping {link.get('url')}: {e}")

    with open(out_path, "w") as f:
        json.dump(all_actions, f, indent=2, ensure_ascii=False)

    print(f"\nExtracted {len(all_actions)} actions in total.")


if __name__ == "__main__":
    main()


