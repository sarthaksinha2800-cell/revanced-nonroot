import logging 
from src import session 
from bs4 import BeautifulSoup

def get_latest_version(app_name: str, config: str) -> str:
    # Try multiple possible Uptodown URL patterns
    possible_names = [
        config['name'],
        f"adobe-{config['name']}",  # For Adobe apps
        config['package'].replace('.', '-'),  # Package name as fallback
    ]
    
    for uptodown_name in possible_names:
        url = f"https://{uptodown_name}.en.uptodown.com/android/versions"
        try:
            response = session.get(url)
            response.raise_for_status()
            content_size = len(response.content)
            logging.info(f"URL:{response.url} [{content_size}/{content_size}] -> \"-\" [1]")
            soup = BeautifulSoup(response.content, "html.parser")
            version_spans = soup.select('#versions-items-list .version')
            versions = [span.text for span in version_spans]
            highest_version = max(versions)
            return highest_version
        except Exception:
            continue
    
    # If all attempts fail
    raise Exception(f"Could not find Uptodown page for {app_name}")

def get_download_link(version: str, app_name: str, config: str) -> str:
    # Try the same patterns as get_latest_version
    possible_names = [
        config['name'],
        f"adobe-{config['name']}",
        config['package'].replace('.', '-'),
    ]
    
    for uptodown_name in possible_names:
        base_url = f"https://{uptodown_name}.en.uptodown.com/android"
        try:
            response = session.get(base_url)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")
            data_code = soup.find('h1', id='detail-app-name')['data-code']

            page = 1
            while True:
                response = session.get(f"{base_url}/apps/{data_code}/versions/{page}")
                response.raise_for_status()
                version_data = response.json().get('data', [])
                
                for entry in version_data:
                    if entry["version"] == version:
                        version_url_parts = entry["versionURL"]
                        version_url = f"{version_url_parts['url']}/{version_url_parts['extraURL']}/{version_url_parts['versionID']}"
                        version_page = session.get(version_url)
                        version_page.raise_for_status()
                        soup = BeautifulSoup(version_page.content, "html.parser")
                        
                        # Check for button type
                        button = soup.find('button', id='detail-download-button')
                        if "download-link-deeplink" in button['onclick']:
                            # Update versionURL by adding '-x'
                            version_url += '-x'
                            version_page = session.get(version_url)
                            version_page.raise_for_status()
                            soup = BeautifulSoup(version_page.content, "html.parser")
                            button = soup.find('button', id='detail-download-button')
                        
                        download_url = button['data-url']
                        return f"https://dw.uptodown.com/dwn/{download_url}"
                
                if all(entry["version"] < version for entry in version_data):
                    break
                page += 1
        except Exception:
            continue
    
    return None
