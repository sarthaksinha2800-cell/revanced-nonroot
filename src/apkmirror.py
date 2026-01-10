import re
import json
import logging
from bs4 import BeautifulSoup
from src import base_url, session

def get_download_link(version: str, app_name: str, config: dict) -> str: 
    criteria = [config['type'], config['arch'], config['dpi']]
    
    # --- UNIVERSAL URL FINDER START ---
    # We split the version to try finding the release page.
    # Some apps (like Prime Video) nest version 3.0.412.2947 under page 3.0.412.
    version_parts = version.split('.')
    found_soup = None
    
    # Loop backwards: Try full version, then strip parts until we find a 200 OK page.
    # Example: tries "3-0-412-2947", then "3-0-412"
    for i in range(len(version_parts), 0, -1):
        current_ver_str = "-".join(version_parts[:i])
        
        # Construct the URL attempt
        url = (f"{base_url}/apk/{config['org']}/{config['name']}/"
               f"{config['name']}-{current_ver_str}-release/")
        
        logging.info(f"Checking potential release URL: {url}")
        
        response = session.get(url)
        if response.status_code == 200:
            content_size = len(response.content)
            logging.info(f"URL:{response.url} [{content_size}/{content_size}] -> Found Page")
            found_soup = BeautifulSoup(response.content, "html.parser")
            break
        elif response.status_code == 404:
            continue
        else:
            response.raise_for_status()
    
    if not found_soup:
        logging.error(f"Could not find any release page for {app_name} {version}")
        return None
    # --- UNIVERSAL URL FINDER END ---

    # Now we are on the correct page (either specific or parent).
    # We must find the specific variant that matches our EXACT version and criteria.
    rows = found_soup.find_all('div', class_='table-row headerFont')
    download_page_url = None
    
    for row in rows:
        row_text = row.get_text()
        
        # CRITICAL CHECK: Ensure the row actually contains our specific version number.
        # This prevents downloading the wrong build (e.g., .557) when on a parent page (3.0.412).
        if version not in row_text:
            continue

        if all(criterion in row_text for criterion in criteria):
            sub_url = row.find('a', class_='accent_color')
            if sub_url:
                download_page_url = base_url + sub_url['href']
                break

    if not download_page_url:
        logging.error(f"Variant {version} not found with criteria {criteria}")
        return None

    # --- STANDARD DOWNLOAD FLOW (Page 2 -> Page 3 -> Link) ---
    response = session.get(download_page_url)
    response.raise_for_status()
    content_size = len(response.content)
    logging.info(f"URL:{response.url} [{content_size}/{content_size}] -> Variant Page")
    soup = BeautifulSoup(response.content, "html.parser")

    sub_url = soup.find('a', class_='downloadButton')
    if sub_url:
        final_download_page_url = base_url + sub_url['href']
        response = session.get(final_download_page_url)
        response.raise_for_status()
        content_size = len(response.content)
        logging.info(f"URL:{response.url} [{content_size}/{content_size}] -> Download Page")
        soup = BeautifulSoup(response.content, "html.parser")

        button = soup.find('a', id='download-link')
        if button:
            return base_url + button['href']

    return None
    

def get_latest_version(app_name: str, config: str) -> str:
    url = f"{base_url}/uploads/?appcategory={config['name']}"

    response = session.get(url)
    response.raise_for_status()
    content_size = len(response.content)
    logging.info(f"URL:{response.url} [{content_size}/{content_size}] -> \"-\" [1]")
    soup = BeautifulSoup(response.content, "html.parser")

    app_rows = soup.find_all("div", class_="appRow")
    version_pattern = re.compile(r'\d+(\.\d+)*(-[a-zA-Z0-9]+(\.\d+)*)*')

    for row in app_rows:
        version_text = row.find("h5", class_="appRowTitle").a.text.strip()
        if "alpha" not in version_text.lower() and "beta" not in version_text.lower():
            match = version_pattern.search(version_text)
            if match:
                return match.group()

    return None
