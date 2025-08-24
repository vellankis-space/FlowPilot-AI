import re
import os
import time
from typing import List, Dict, Tuple, Optional
import requests
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

def _clean_text(value: str) -> str:
    """Clean and normalize text content"""
    if not value:
        return ""
    # Remove extra whitespace
    return re.sub(r"\s+", " ", value).strip()

def _make_session() -> requests.Session:
    """Create a requests session with retry logic and proper headers"""
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
    """Detect and normalize table headers"""
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

def _first_paragraph_after(heading: Tag) -> str:
    """Look ahead until next heading for the first non-empty paragraph"""
    tag = heading
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
    """Determine the heading level of a BeautifulSoup Tag"""
    if not isinstance(tag, Tag):
        return 99
    if tag.name and tag.name.startswith("h") and len(tag.name) == 2 and tag.name[1].isdigit():
        return int(tag.name[1])
    return 99

def _collect_sectioned_tables(heading: Tag) -> List[Tuple[str, Tag]]:
    """Collect tables within a section defined by a heading"""
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
            if "input parameters" in section_text or ("input" in section_text and "parameter" in section_text):
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

def _project_path(*parts: str) -> str:
    """Get absolute path to a file in the project, relative to the backend directory"""
    base_dir = os.path.dirname(os.path.abspath(__file__)) # backend/
    return os.path.join(base_dir, *parts)
