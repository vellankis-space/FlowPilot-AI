import json
import os
import re
import time
import logging
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PackageInfo:
    def __init__(self, name: str, url: str):
        self.name = name
        self.url = url
        self.actions = []  # List of tuples (action_name, description)

    def to_dict(self) -> Dict:
        return {
            "package": self.name,
            "actions": [
                {
                    "name": name,
                    "description": desc
                }
                for name, desc in self.actions
            ]
        }


class ScrapingError(Exception):
    """Custom exception for scraping errors"""
    pass

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

def get_package_actions(session: requests.Session, package_url: str) -> List[Tuple[str, str]]:
    """Extract actions and their descriptions from a package page"""
    try:
        response = session.get(package_url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        
        # First try to find actions table with specific title
        actions_table = None
        for heading in soup.find_all(['h1', 'h2', 'h3']):
            if 'Actions in the' in heading.get_text():
                actions_table = heading.find_next('table')
                break
        
        # If no table found with that title, look for any suitable table with action information
        if not actions_table:
            tables = soup.find_all('table')
            for table in tables:
                headers = _detect_table_headers(table)
                if any('action' in h.lower() for h in headers):
                    actions_table = table
                    break
                    
        if not actions_table:
            return []
            
        actions = []
        rows = actions_table.find_all('tr')[1:]  # Skip header row
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                action_name = _clean_text(cells[0].get_text())
                description = _clean_text(cells[1].get_text())
                if action_name and description:
                    actions.append((action_name, description))
                    
        return actions
        
    except Exception as e:
        logger.error(f"Error scraping package page {package_url}: {str(e)}")
        return []




def find_section(root: Tag, keywords: List[str], max_depth: int = 3) -> Optional[Tag]:
    """Find a section by looking for headings containing keywords"""
    for depth in range(1, max_depth + 1):
        for heading in root.find_all(f'h{depth}'):
            if any(keyword.lower() in heading.get_text().lower() for keyword in keywords):
                return get_section_content(heading)
    return None

def get_section_content(heading: Tag) -> Tag:
    """Get all content belonging to a section until the next heading of same or higher level"""
    content = []
    current = heading.find_next_sibling()
    heading_level = int(heading.name[1])
    
    while current and (not current.name.startswith('h') or 
                      int(current.name[1]) > heading_level):
        content.append(str(current))
        current = current.find_next_sibling()
    
    return BeautifulSoup(''.join(content), 'html.parser')

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

def extract_last_updated(soup: BeautifulSoup) -> Optional[str]:
    """Extract the last updated date from the page"""
    date_patterns = [
        r"Last updated:?\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
        r"Updated:?\s*(\d{1,2}/\d{1,2}/\d{4})",
        r"Modified:?\s*(\d{4}-\d{2}-\d{2})",
    ]
    
    # Look for date in meta tags first
    meta_modified = soup.find("meta", {"name": ["last-modified", "date", "last-updated"]})
    if meta_modified and meta_modified.get("content"):
        return meta_modified["content"]
    
    # Look for date patterns in text
    text = soup.get_text()
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return None

def scrape_automation_anywhere() -> List[Dict]:
    """
    Main function to scrape Automation Anywhere documentation.
    Returns a list of packages with their actions.
    """
    base_url = "https://docs.automationanywhere.com/bundle/enterprise-v2019/page/enterprise-cloud/topics/aae-client/bot-creator/using-the-workbench/cloud-build-action-packages.html"
    output_file = "backend/data/automation_anywhere_actions_detailed.json"
    
    session = _make_session()
    packages = []
    processed_packages = set()
    # Load already processed packages from output file
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)
                for pkg in existing:
                    processed_packages.add(pkg.get('package'))
                packages.extend(existing)
        except Exception as e:
            logger.warning(f"Could not read output file: {e}")

    try:
        # Get the main package listing page
        response = session.get(base_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        # Find the table that lists all packages
        package_tables = soup.find_all('table')
        for table in package_tables:
            rows = table.find_all('tr')[1:]  # Skip header row
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 2:
                    # Look for a link in the first cell
                    link = cells[0].find('a')
                    if link and link.get('href'):
                        name = _clean_text(cells[0].get_text())
                        url = urljoin(base_url, link['href'])
                        if name in processed_packages:
                            logger.info(f"Skipping already processed package: {name}")
                            continue
                        package = PackageInfo(name, url)

                        # Get actions for this package
                        actions = get_package_actions(session, url)
                        package.actions.extend(actions)

                        if package.actions:  # Only add packages that have actions
                            packages.append(package.to_dict())
                            processed_packages.add(name)

                        # Save progress after each package
                        os.makedirs(os.path.dirname(output_file), exist_ok=True)
                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump(packages, f, indent=2, ensure_ascii=False)

                        # Be nice to the server
                        time.sleep(1)

        return packages

    except Exception as e:
        logger.error(f"Error in main scraping function: {str(e)}")
        return []

if __name__ == "__main__":
    scrape_automation_anywhere()









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







def _project_path(*parts: str) -> str:
    """Get absolute path to a file in the project"""
    base_dir = os.path.dirname(__file__)  # backend/
    return os.path.join(base_dir, *parts)

def extract_packages_from_main_page(session: requests.Session) -> List[PackageInfo]:
    """Extract package information from the main commands panel page"""
    url = "https://docs.automationanywhere.com/bundle/enterprise-v2019/page/enterprise-cloud/topics/aae-client/bot-creator/using-the-workbench/cloud-commands-panel.html"
    
    try:
        response = session.get(url, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")
        
        packages = []
        # Look for package links in the main content
        main = soup.find("main") or soup
        
        for link in main.find_all('a'):
            href = link.get('href')
            text = _clean_text(link.get_text())
            
            # Look for links that contain "package" and end with "html"
            if href and 'package' in href.lower() and href.endswith('.html'):
                # Convert relative URL to absolute
                full_url = urljoin(url, href)
                packages.append(PackageInfo(text, full_url))
                
        return packages
        
    except Exception as e:
        logger.error(f"Error scraping main page: {str(e)}")
        return []

def main() -> None:
    """Main execution function"""
    out_path = _project_path("data", "automation_anywhere_actions_detailed.json")
    session = _make_session()

    # Get package list from main page
    logger.info("Fetching package list from main page...")
    packages = extract_packages_from_main_page(session)
    
    if not packages:
        logger.error("No packages found on main page")
        return
        
    logger.info(f"Found {len(packages)} packages to process")
    
    # Process each package
    for package in packages:
        try:
            logger.info(f"Processing package: {package.name}")
            actions = get_package_actions(session, package.url)
            package.actions.extend(actions)
            time.sleep(1)  # Respectful delay
        except Exception as e:
            logger.error(f"Error processing package {package.name}: {str(e)}")
            continue
    
    # Convert to final format and save
    output = [pkg.to_dict() for pkg in packages if pkg.actions]
    
    try:
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        total_actions = sum(len(pkg.actions) for pkg in packages)
        logger.info(f"Successfully extracted {total_actions} actions "
                   f"from {len(output)} packages")
    except Exception as e:
        logger.error(f"Error saving results: {str(e)}")

if __name__ == "__main__":
    main()


