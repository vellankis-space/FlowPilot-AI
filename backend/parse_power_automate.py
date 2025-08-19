
from bs4 import BeautifulSoup
import json

# Load the HTML file
with open('backend/data/power_automate_docs.html', 'r') as f:
    html_content = f.read()

# Parse the HTML
soup = BeautifulSoup(html_content, 'html.parser')

# Find all action links
action_links = []
for td in soup.find_all('td'):
    a = td.find('a')
    if a and a.has_attr('href'):
        action_links.append({
            "action": a.text.strip(),
            "url": "https://learn.microsoft.com/en-us/power-automate/desktop-flows/" + a['href']
        })

# Save the extracted links to a JSON file
with open('backend/data/power_automate_action_links.json', 'w') as f:
    json.dump(action_links, f, indent=2)

print(f"Extracted {len(action_links)} action links.")
