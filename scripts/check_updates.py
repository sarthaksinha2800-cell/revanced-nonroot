#!/usr/bin/env python3
import json
import requests
import os
import sys
from datetime import datetime
import re

def get_latest_version_from_apkmirror(package_name):
    """Get latest version from APKMirror using their API"""
    try:
        # Try different API endpoints
        endpoints = [
            f"https://api.apkmirror.com/v2/apps/{package_name}/",
            f"https://www.apkmirror.com/wp-json/apkm/v1/app_exists/?pname={package_name}"
        ]
        
        for endpoint in endpoints:
            try:
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(endpoint, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    # Try different JSON paths
                    if 'data' in data and 'app' in data['data']:
                        return data['data']['app'].get('latest_release', {}).get('version')
                    elif 'version' in data:
                        return data['version']
            except:
                continue
    except Exception as e:
        print(f"Error checking {package_name}: {e}")
    
    return None

def extract_package_name_from_url(url):
    """Extract package name from APK URL"""
    patterns = [
        r'com\.\w+(?:\.\w+)*',  # com.package.name
        r'apk/\w+/[\w-]+/([\w-]+)-'  # From APKMirror URL
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(0) if pattern.startswith('com') else match.group(1)
    
    return None

def update_patch_config():
    """Update patch-config.json with latest versions"""
    with open('patch-config.json', 'r') as f:
        config = json.load(f)
    
    updated = False
    for app in config.get('patch_list', []):
        source = app.get('source', '')
        if source and 'apkmirror.com' in source:
            # Extract package name from URL
            package_name = extract_package_name_from_url(source)
            if package_name:
                latest_version = get_latest_version_from_apkmirror(package_name)
                if latest_version:
                    # Extract current version from URL
                    current_match = re.search(r'(\d+\.\d+\.\d+)', source)
                    if current_match:
                        current_version = current_match.group(1)
                        if current_version != latest_version:
                            print(f"Update available for {app.get('app_name', 'unknown')}: {current_version} -> {latest_version}")
                            # Update the URL with new version
                            new_url = re.sub(r'\d+\.\d+\.\d+', latest_version, source)
                            app['source'] = new_url
                            updated = True
                    else:
                        print(f"Could not extract version from URL: {source}")
    
    if updated:
        # Save updated config
        with open('patch-config.json', 'w') as f:
            json.dump(config, f, indent=2)
        
        print("Updated patch-config.json")
        
        # Return update info for GitHub Actions
        print(f"::set-output name=has_updates::true")
        print(f"::set-output name=updated_apps::{json.dumps([app.get('app_name') for app in config['patch_list'] if 'updated' in app])}")
    else:
        print("No updates found")
        print(f"::set-output name=has_updates::false")
    
    return updated

if __name__ == "__main__":
    update_patch_config()
