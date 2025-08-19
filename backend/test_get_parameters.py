import requests
from bs4 import BeautifulSoup

def get_parameters(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        parameters = []
        # Find all tables that might contain parameters
        tables = soup.find_all('table')
        for table in tables:
            # Check for a header row with 'Argument'
            header = table.find('thead')
            if header and 'Argument' in header.text:
                rows = table.find('tbody').find_all('tr')
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 5:
                        parameters.append({
                            "Argument": cols[0].text.strip(),
                            "Optional": cols[1].text.strip(),
                            "Accepts": cols[2].text.strip(),
                            "Default Value": cols[3].text.strip(),
                            "Description": cols[4].text.strip()
                        })
        return parameters
    except Exception as e:
        print(f"Error scraping parameters from {url}: {e}")
        return []

# Test with a known URL that has parameters
test_url = "https://learn.microsoft.com/en-us/power-automate/desktop-flows/actions-reference/excel#resize-columnsrows-in-excel-worksheet"

print(f"Testing get_parameters with URL: {test_url}")
result_parameters = get_parameters(test_url)
print("Resulting parameters:")
for param in result_parameters:
    print(param)