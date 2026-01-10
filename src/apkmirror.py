import re
import logging
from bs4 import BeautifulSoup
from src import base_url, session

def get_download_link(version: str, app_name: str, config: dict) -> str: 
    criteria = [config['type'], config['arch'], config['dpi']]
    version_parts = version.split('.')
    found_soup = None
    
    # Universal Fallback Strategy:
    # Handles Lightroom (9.3.0 -> 9.3) and Prime Video (3.0.412.2947 -> 3.0.412)
    # It tries 9.3.0, then 9.3, then 9 until it finds a valid page.
    for i in range(len(version_parts), 0, -1):
        current_ver_str = "-".join(version_parts[:i])
        url = (f"{base_url}/apk/{config['org']}/{config['name']}/"
               f"{config['name']}-{current_ver_str}-release/")
        
        logging.info(f"Checking APKMirror URL: {url}")
        response = session.get(url)
        
        if response.status_code == 200:
            logging.info(f"Found valid release page: {url}")
            found_soup = BeautifulSoup(response.content, "html.parser")
            break
        elif response.status_code == 403:
            logging.error("Access Forbidden. Your User-Agent might be flagged or blocked.")
            return None
        # If 404, the loop continues to the next (broader) version segment

    if not found_soup:
        logging.error(f"No release page found for {app_name} version {version}")
        return None

    # Search for the exact variant in the table of the found page
    rows = found_soup.find_all('div', class_='table-row headerFont')
    download_page_url = None
    for row in rows:
        row_text = row.get_text()
        
        # Verify the EXACT target version is in this row (crucial for nested versions)
        # and that it matches your JSON criteria (arch, dpi, type)
        if version in row_text and all(criterion in row_text for criterion in criteria):
            sub_url = row.find('a', class_='accent_color')
            if sub_url:
                download_page_url = base_url + sub_url['href']
                break

    if not download_page_url:
        logging.error(f"Variant {version} with criteria {criteria} not found on this page.")
        return None

    # Step 2: Navigate to the intermediate download page
    response = session.get(download_page_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    sub_url = soup.find('a', class_='downloadButton')
    if sub_url:
        # Step 3: Navigate to the final page containing the actual file link
        final_page_url = base_url + sub_url['href']
        response = session.get(final_page_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "html.parser")

        button = soup.find('a', id='download-link')
        if button:
            return base_url + button['href']

    return None

def get_latest_version(app_name: str, config: dict) -> str:
    url = f"{base_url}/uploads/?appcategory={config['name']}"
    response = session.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")

    app_rows = soup.find_all("div", class_="appRow")
    version_pattern = re.compile(r'\d+(\.\d+)*(-[a-zA-Z0-9]+(\.\d+)*)*')

    for row in app_rows:
        title_tag = row.find("h5", class_="appRowTitle")
        if title_tag and title_tag.a:
            version_text = title_tag.a.text.strip()
            if "alpha" not in version_text.lower() and "beta" not in version_text.lower():
                match = version_pattern.search(version_text)
                if match:
                    return match.group()
    return None
