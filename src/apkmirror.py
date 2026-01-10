import re
import json
import logging
from bs4 import BeautifulSoup
from src import base_url, session

def get_download_link(version: str, app_name: str, config: dict) -> str: 
    criteria = [config['type'], config['arch'], config['dpi']]
    
    # --- UNIVERSAL URL FINDER START ---
    # We split the version to try finding the release page.
    version_parts = version.split('.')
    found_soup = None
    
    # Use release_prefix if available, otherwise use app name
    release_name = config.get('release_prefix', config['name'])
    
    # Loop backwards: Try full version, then strip parts until we find a 200 OK page.
    for i in range(len(version_parts), 0, -1):
        current_ver_str = "-".join(version_parts[:i])
        
        # Try multiple URL patterns
        url_patterns = []
        
        # Pattern 1: With release_name (main pattern)
        url_patterns.append(f"{base_url}/apk/{config['org']}/{config['name']}/{release_name}-{current_ver_str}/")
        url_patterns.append(f"{base_url}/apk/{config['org']}/{config['name']}/{release_name}-{current_ver_str}-release/")
        
        # Pattern 2: With app name (fallback for backward compatibility)
        if release_name != config['name']:
            url_patterns.append(f"{base_url}/apk/{config['org']}/{config['name']}/{config['name']}-{current_ver_str}/")
            url_patterns.append(f"{base_url}/apk/{config['org']}/{config['name']}/{config['name']}-{current_ver_str}-release/")
        
        for url in url_patterns:
            logging.info(f"Checking potential release URL: {url}")
            
            response = session.get(url)
            if response.status_code == 200:
                content_size = len(response.content)
                logging.info(f"URL:{response.url} [{content_size}/{content_size}] -> Found Page")
                found_soup = BeautifulSoup(response.content, "html.parser")
                break  # Break out of URL patterns loop
            elif response.status_code == 404:
                continue  # Try next pattern
            else:
                # For other status codes, log but continue
                logging.warning(f"URL {url} returned status {response.status_code}")
                continue
        
        if found_soup:
            break  # Break out of version parts loop
    
    if not found_soup:
        logging.error(f"Could not find any release page for {app_name} {version}")
        return None

    # We must find the specific variant that matches our criteria.
    rows = found_soup.find_all('div', class_='table-row headerFont')
    download_page_url = None
    
    # Create a regex pattern to match the version (allowing build numbers)
    # This will match "7.20", "7.20.build129", "7.20.build128", etc.
    version_pattern = re.escape(version) + r'(\.\w+)*'  # Allows .build129, .build128, etc.
    
    for row in rows:
        row_text = row.get_text()
        
        # Check if the row contains a version that starts with our target version
        # First, extract the version from the row text
        version_match = re.search(r'(\d+(\.\d+)+(\.\w+)*)', row_text)
        if version_match:
            row_version = version_match.group(1)
            # Check if this row version starts with our target version
            if row_version.startswith(version):
                # Now check the criteria
                if all(criterion in row_text for criterion in criteria):
                    sub_url = row.find('a', class_='accent_color')
                    if sub_url:
                        download_page_url = base_url + sub_url['href']
                        break

    if not download_page_url:
        # If still not found, try looser matching - just find first matching criteria
        for row in rows:
            row_text = row.get_text()
            if all(criterion in row_text for criterion in criteria):
                # Check if it's any version of our app (not just exact version)
                sub_url = row.find('a', class_='accent_color')
                if sub_url:
                    download_page_url = base_url + sub_url['href']
                    # Extract the actual version from this row for logging
                    version_match = re.search(r'(\d+(\.\d+)+(\.\w+)*)', row_text)
                    if version_match:
                        actual_version = version_match.group(1)
                        logging.warning(f"Using version {actual_version} instead of {version}")
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
    
def get_latest_version(app_name: str, config: dict) -> str:
    # First try: get from main app page
    try:
        main_url = f"{base_url}/apk/{config['org']}/{config['name']}/"
        response = session.get(main_url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            # Try to find version in the page
            version_elem = soup.find('span', string=re.compile(r'\d+\.\d+'))
            if version_elem:
                version_text = version_elem.text.strip()
                match = re.search(r'(\d+(\.\d+)+)', version_text)
                if match:
                    return match.group(1)
    except:
        pass  # If fails, continue to original method
    
    # Original method (keep exactly as you had it)
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
                version = match.group()
                version_parts = version.split('.')
                base_version_parts = []
                for part in version_parts:
                    if part.isdigit():
                        base_version_parts.append(part)
                    else:
                        break
                if base_version_parts:
                    return '.'.join(base_version_parts)

    return None
