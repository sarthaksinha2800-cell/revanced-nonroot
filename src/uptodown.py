import logging 
import re
from src import session 
from bs4 import BeautifulSoup

def get_app_base_url(app_name: str, config: dict) -> str:
    """Finds the correct Uptodown subdomain using the package name."""
    # Try the guessed URL first
    guessed_url = f"https://{config['name']}.en.uptodown.com/android"
    try:
        res = session.get(guessed_url, timeout=10)
        if res.status_code == 200:
            return guessed_url
    except:
        pass

    # If guess fails (like Lightroom), search by package name
    logging.info(f"Guess failed for {app_name}, searching Uptodown...")
    search_url = f"https://en.uptodown.com/android/search"
    res = session.get(search_url, params={'q': config['package']})
    soup = BeautifulSoup(res.content, 'html.parser')
    
    # Look for the first search result link
    # Uptodown search results usually have the link in a div with class 'name'
    result = soup.find('div', class_='name')
    if result and result.parent.has_attr('href'):
        found_url = result.parent['href']
        logging.info(f"Found correct URL via search: {found_url}")
        return found_url.rstrip('/')

    # Final fallback if search fails
    return guessed_url

def get_latest_version(app_name: str, config: dict) -> str:
    base_url = get_app_base_url(app_name, config)
    url = f"{base_url}/versions"

    response = session.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    
    # Uptodown lists versions in a specific list; get the first (latest) one
    version_span = soup.select_one('#versions-items-list .version span.v')
    if version_span:
        return version_span.text.strip()
    
    return None

def get_download_link(version: str, app_name: str, config: dict) -> str:
    base_url = get_app_base_url(app_name, config)
    
    # Get the internal data-code required for the AJAX version API
    response = session.get(f"{base_url}/versions")
    response.raise_for_status()
    soup = BeautifulSoup(response.content, "html.parser")
    
    name_tag = soup.find('h1', id='detail-app-name')
    if not name_tag or not name_tag.has_attr('data-code'):
        logging.error("Could not find data-code for Uptodown AJAX request.")
        return None
    
    data_code = name_tag['data-code']
    page = 1
    
    while True:
        # Uptodown uses this endpoint to load more versions
        api_url = f"{base_url}/apps/{data_code}/versions/{page}"
        response = session.get(api_url)
        if response.status_code != 200:
            break
            
        version_data = response.json().get('data', [])
        if not version_data:
            break
        
        for entry in version_data:
            if entry["version"].strip() == version.strip():
                v_url_info = entry["versionURL"]
                # Build the page URL for the specific version
                version_page_url = f"{v_url_info['url']}/{v_url_info['extraURL']}/{v_url_info['versionID']}"
                
                return extract_direct_link(version_page_url)
        
        # If we've passed where the version would be alphabetically/numerically, stop
        # (Simple heuristic: if the last entry is already older than our target)
        page += 1
        if page > 10: # Safety break
            break

    return None

def extract_direct_link(version_page_url: str) -> str:
    """Navigates the download button logic to get the final .apk/.xapk link."""
    res = session.get(version_page_url)
    soup = BeautifulSoup(res.content, "html.parser")
    button = soup.find('button', id='detail-download-button')
    
    if not button:
        return None

    # Handle XAPK/DeepLink redirects
    if button.has_attr('onclick') and "download-link-deeplink" in button['onclick']:
        res = session.get(f"{version_page_url}-x")
        soup = BeautifulSoup(res.content, "html.parser")
        button = soup.find('button', id='detail-download-button')

    if button and button.has_attr('data-url'):
        download_id = button['data-url']
        # The dw subdomain is where the actual files are hosted
        return f"https://dw.uptodown.com/dwn/{download_id}"
    
    return None
