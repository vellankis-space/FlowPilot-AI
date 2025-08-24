import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin

# Main index page for Automation Anywhere 360 packages
INDEX_URL = "https://docs.automationanywhere.com/bundle/enterprise-v2019/page/enterprise-cloud/topics/aae-client/bot-creator/commands/packages-releases-overview.html"
BASE_URL = "https://docs.automationanywhere.com"

output_file = "backend/data/automation_anywhere_action_links.json"

def get_package_links():
    session = requests.Session()
    resp = session.get(INDEX_URL, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")
    links = []
    # Find all anchor tags that likely point to package documentation
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        # Heuristic: look for links containing 'package' and not 'update' or 'release-notes'
        if "package" in href and not any(x in href for x in ["update", "release-notes"]):
            full_url = urljoin(BASE_URL, href)
            links.append({
                "package": text or href.split("/")[-1],
                "url": full_url
            })
    return links

def main():
    links = get_package_links()
    with open(output_file, "w") as f:
        json.dump(links, f, indent=2, ensure_ascii=False)
    print(f"Extracted {len(links)} package action documentation links to {output_file}")

if __name__ == "__main__":
    main()
