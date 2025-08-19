
from bs4 import BeautifulSoup
import json

# Load the HTML file
with open('backend/data/uipath_docs.html', 'r') as f:
    html_content = f.read()

# Parse the HTML
soup = BeautifulSoup(html_content, 'html.parser')

# Find all action links
action_links = []
# Based on manual inspection, the links are in divs with class 'col-md-4'
for div in soup.find_all('div', class_='col-md-4'):
    a = div.find('a')
    if a and a.has_attr('href'):
        action_links.append({
            "action": a.text.strip(),
            "url": "https://docs.uipath.com" + a['href']
        })

# Save the extracted links to a JSON file
with open('backend/data/uipath_action_links.json', 'w') as f:
    json.dump(action_links, f, indent=2)

print(f"Extracted {len(action_links)} action links.")
