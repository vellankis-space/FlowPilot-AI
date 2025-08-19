import json
import os
import re
import time
from typing import Dict, List, Tuple

import requests
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

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


def _classify_parameter_type(headers: List[str]) -> str:
    headers_joined = " ".join(h.lower() for h in headers)
    if "output" in headers_joined or "outputs" in headers_joined:
        return "Output"
    if "input" in headers_joined or "argument" in headers_joined or "parameter" in headers_joined:
        return "Input"
    return "Unknown"


def get_parameters(table_soup: Tag) -> Tuple[str, List[Dict[str, str]]]:
    parameters: List[Dict[str, str]] = []
    headers = _detect_table_headers(table_soup)
    parameter_type = _classify_parameter_type(headers)

    # Build a normalized key map for typical columns
    normalized_headers: List[str] = []
    for header in headers:
        h = header.lower()
        if "argument" in h or h in ("name",):
            normalized_headers.append("Name")
        elif "optional" in h:
            normalized_headers.append("Optional")
        elif "accepts" in h or "type" in h:
            normalized_headers.append("Accepts")
        elif "default" in h:
            normalized_headers.append("Default Value")
        elif "description" in h:
            normalized_headers.append("Description")
        elif "variable" in h:
            normalized_headers.append("Variable")
        else:
            normalized_headers.append(header)

    tbody = table_soup.find("tbody") or table_soup
    rows = tbody.find_all("tr") if tbody else []
    # Skip header row if it exists within tbody
    if rows and rows[0].find_all("th"):
        rows = rows[1:]

    for row in rows:
        cells = row.find_all("td")
        if not cells:
            continue
        cell_texts = [_clean_text(c.get_text()) for c in cells]
        # Align cells to headers by position
        detail: Dict[str, str] = {}
        for idx, value in enumerate(cell_texts):
            key = normalized_headers[idx] if idx < len(normalized_headers) else f"Col{idx+1}"
            detail[key] = value

        # Ensure we have at least Name/Description like fields
        if detail:
            parameters.append(detail)

    return parameter_type, parameters


def _first_paragraph_after(heading: Tag) -> str:
    tag = heading
    # Look ahead until next heading for the first non-empty paragraph
    while tag:
        tag = tag.find_next_sibling()
        if tag is None:
            break
        if isinstance(tag, Tag) and tag.name in ("h2", "h3", "h4"):
            break
        if isinstance(tag, Tag) and tag.name == "p":
            text = _clean_text(tag.get_text())
            if text:
                return text
    return ""


def _heading_level(tag: Tag) -> int:
    if not isinstance(tag, Tag):
        return 99
    if tag.name and tag.name.startswith("h") and len(tag.name) == 2 and tag.name[1].isdigit():
        return int(tag.name[1])
    return 99


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
                # next action or higher-level section begins
                break
            # lower-level heading inside this action -> may denote a section
            section_text = _clean_text(tag.get_text()).lower()
            if "input parameters" in section_text:
                current_section = "Input parameters"
            elif "variables produced" in section_text or "outputs" in section_text or "output" in section_text:
                current_section = "Variables produced"
            elif "exceptions" in section_text:
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


def _map_input_parameters(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    mapped: List[Dict[str, str]] = []
    for row in rows:
        argument = row.get("Name") or row.get("Argument") or row.get("Variable") or row.get("Col1")
        ptype = row.get("Accepts") or row.get("Type") or row.get("Col2")
        description = row.get("Description") or row.get("Col3")
        item: Dict[str, str] = {}
        if argument:
            item["Argument"] = argument
        if ptype:
            item["Type"] = ptype
        if description:
            item["Description"] = description
        if item:
            mapped.append(item)
    return mapped


def _map_variables_produced(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    mapped: List[Dict[str, str]] = []
    for row in rows:
        argument = row.get("Variable") or row.get("Name") or row.get("Argument") or row.get("Col1")
        ptype = row.get("Accepts") or row.get("Type") or row.get("Col2")
        description = row.get("Description") or row.get("Col3")
        item: Dict[str, str] = {}
        if argument:
            item["Argument"] = argument
        if ptype:
            item["Type"] = ptype
        if description:
            item["Description"] = description
        if item:
            mapped.append(item)
    return mapped


def _map_exceptions(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    mapped: List[Dict[str, str]] = []
    for row in rows:
        ex = row.get("Exception") or row.get("Name") or row.get("Col1")
        description = row.get("Description") or row.get("Col2")
        item: Dict[str, str] = {}
        if ex:
            item["Exception"] = ex
        if description:
            item["Description"] = description
        if item:
            mapped.append(item)
    return mapped


def parse_category_page(session: requests.Session, url: str, category: str) -> List[Dict]:
    print(f"Scraping {url}...")
    response = session.get(url, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    main = soup.find("main", id="main") or soup
    content_root = main

    actions: List[Dict] = []
    # Prefer lower-level headings first to avoid page title h1/h2; most actions are h3/h4
    headings = content_root.find_all(["h4", "h3", "h2"])  # order matters: h4 first
    for heading in headings:
        action_name = _clean_text(heading.get_text())
        if not action_name or len(action_name) < 2:
            continue

        # Skip generic or subsection headings
        generic = {
            "in this article",
            "feedback",
            "additional resources",
            "input parameters",
            "variables produced",
            "exceptions",
            "valid keys",
            "request builder parameters",
            "attachments parameters",
        }
        if action_name.strip().lower() in generic:
            continue

        action_description = _first_paragraph_after(heading) or "N/A"
        sectioned_tables = _collect_sectioned_tables(heading)

        input_params: List[Dict[str, str]] = []
        variables_produced: List[Dict[str, str]] = []
        exceptions: List[Dict[str, str]] = []

        for section, table in sectioned_tables:
            headers = _detect_table_headers(table)
            headers_joined = " ".join(h.lower() for h in headers)
            _, rows = get_parameters(table)
            if not rows:
                continue
            if section == "Exceptions" or "exception" in headers_joined:
                mapped = _map_exceptions(rows)
                if mapped:
                    exceptions.extend(mapped)
            elif section == "Variables produced" or "variable" in headers_joined or "output" in headers_joined:
                mapped = _map_variables_produced(rows)
                if mapped:
                    variables_produced.extend(mapped)
            else:
                mapped = _map_input_parameters(rows)
                if mapped:
                    input_params.extend(mapped)

        # If no relevant data found, skip this action
        if not (input_params or variables_produced or exceptions):
            continue

        actions.append({
                "tool": "Power Automate",
            "category": category,
                "action": action_name,
                "description": action_description,
            "Input parameters": input_params,
            "Variables produced": variables_produced,
            "Exceptions": exceptions,
        })
        time.sleep(0.2)

    return actions


def _project_path(*parts: str) -> str:
    base_dir = os.path.dirname(__file__)  # backend/
    return os.path.join(base_dir, *parts)


def main() -> None:
    links_path = _project_path("data", "power_automate_action_links.json")
    out_path = _project_path("data", "power_automate_actions_detailed.json")

    with open(links_path, "r") as f:
        action_links = json.load(f)

    session = _make_session()
    all_actions: List[Dict] = []

    for link in action_links:
        try:
            category = link.get("action", "Unknown")
            url = link["url"]
            actions = parse_category_page(session, url, category)
            all_actions.extend(actions)
            time.sleep(0.5)
        except Exception as e:
            print(f"Error scraping {link.get('url')}: {e}")

    with open(out_path, "w") as f:
        json.dump(all_actions, f, indent=2, ensure_ascii=False)
    print(f"\nExtracted {len(all_actions)} actions in total.")


if __name__ == "__main__":
    main()
