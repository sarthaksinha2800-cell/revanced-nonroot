import logging 
from src import session 
from bs4 import BeautifulSoup
import re

def get_latest_version(app_name: str, config: dict) -> str:
    # For Adobe Lightroom, we need to use "adobe-lightroom-mobile"
    if app_name == "lightroom" and "adobe" in config.get("package", ""):
        uptodown_name = "adobe-lightroom-mobile"
    else:
        uptodown_name = config.get('name', app_name)
    
    url = f"https://{uptodown_name}.en.uptodown.com/android/versions"
    
    response = session.get(url)
    response.raise_for_status()
    content_size = len(response.content)
    logging.info(f"Uptodown URL:{response.url} [{content_size}/{content_size}] -> \"-\" [1]")
    soup = BeautifulSoup(response.content, "html.parser")
    version_spans = soup.select('#versions-items-list .version')
    versions = [span.text for span in version_spans]
    
    if not versions:
        raise Exception(f"No versions found for {app_name} on Uptodown")
    
    highest_version = max(versions)
    return highest_version

def get_download_link(version: str, app_name: str, config: dict) -> str:
    # For Adobe Lightroom, we need to use "adobe-lightroom-mobile"
    if app_name == "lightroom" and "adobe" in config.get("package", ""):
        uptodown_name = "adobe-lightroom-mobile"
    else:
        uptodown_name = config.get('name', app_name)
    
    base_url = f"https://{uptodown_name}.en.uptodown.com/android"
    
    # First, get the data-code
    response = session.get(f"{base_url}/versions")
    response.raise_for_status()
    
    soup = BeautifulSoup(response.content, "html.parser")
    data_code = soup.find('h1', id='detail-app-name')['data-code']

    # Search through version pages
    page = 1
    while True:
        response = session.get(f"{base_url}/apps/{data_code}/versions/{page}")
        response.raise_for_status()
        version_data = response.json().get('data', [])
        
        if not version_data:
            break
            
        for entry in version_data:
            if entry["version"] == version:
                version_url_parts = entry["versionURL"]
                version_url = f"{version_url_parts['url']}/{version_url_parts['extraURL']}/{version_url_parts['versionID']}"
                
                # Get the download page
                version_page = session.get(version_url)
                version_page.raise_for_status()
                soup = BeautifulSoup(version_page.content, "html.parser")
                
                # Find the download button
                button = soup.find('button', id='detail-download-button')
                if not button:
                    continue
                    
                # Check if we need to use the -x variant
                onclick = button.get('onclick', '')
                if "download-link-deeplink" in onclick:
                    version_url += '-x'
                    version_page = session.get(version_url)
                    version_page.raise_for_status()
                    soup = BeautifulSoup(version_page.content, "html.parser")
                    button = soup.find('button', id='detail-download-button')
                
                if button and 'data-url' in button.attrs:
                    download_url = button['data-url']
                    return f"https://dw.uptodown.com/dwn/{download_url}"
        
        # Check if we should continue to next page
        if all(entry["version"] < version for entry in version_data):
            break
        page += 1
    
    logging.error(f"Version {version} not found for {app_name} on Uptodown")
    return None
