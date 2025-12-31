#!/usr/bin/env python3
import json
import os
import sys
import requests
from datetime import datetime

def check_apkmirror_update(config_file):
    """Check for updates for APKMirror config"""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # If version is empty or we want to check for latest
        if config.get('version') == '':
            package = config.get('package', '')
            if not package:
                return False
            
            # Try to get latest version from APKMirror API
            try:
                # This is a simplified approach - you might need to adjust based on actual APKMirror structure
                url = f"https://api.apkmirror.com/v2/apps/{package}/"
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = requests.get(url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    latest_version = data.get('data', {}).get('app', {}).get('latest_release', {}).get('version')
                    
                    if latest_version:
                        config['version'] = latest_version
                        with open(config_file, 'w') as f:
                            json.dump(config, f, indent=2)
                        return True
            except:
                pass
        
        # Check if we should check for newer version even if version is specified
        # This could be done by comparing with APKMirror
        return False
        
    except Exception as e:
        print(f"Error checking {config_file}: {e}")
        return False

def check_apkpure_update(config_file):
    """Check for updates for APKPure config"""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        if config.get('version') == '':
            # You would need to implement APKPure API call here
            # For now, return False as placeholder
            return False
    except Exception as e:
        print(f"Error checking {config_file}: {e}")
    
    return False

def check_uptodown_update(config_file):
    """Check for updates for Uptodown config"""
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        if config.get('version') == '':
            # You would need to implement Uptodown API call here
            # For now, return False as placeholder
            return False
    except Exception as e:
        print(f"Error checking {config_file}: {e}")
    
    return False

def main():
    # Read patch-config.json
    with open('patch-config.json', 'r') as f:
        patch_config = json.load(f)
    
    updated = False
    
    # Check each app in patch list
    for app_config in patch_config['patch_list']:
        app_name = app_config['app_name']
        
        # Check all possible app config locations
        app_dirs = ['apps/apkmirror', 'apps/apkpure', 'apps/uptodown']
        
        for app_dir in app_dirs:
            config_file = f"{app_dir}/{app_name}.json"
            
            if os.path.exists(config_file):
                if app_dir == 'apps/apkmirror':
                    if check_apkmirror_update(config_file):
                        print(f"Updated {config_file}")
                        updated = True
                elif app_dir == 'apps/apkpure':
                    if check_apkpure_update(config_file):
                        print(f"Updated {config_file}")
                        updated = True
                elif app_dir == 'apps/uptodown':
                    if check_uptodown_update(config_file):
                        print(f"Updated {config_file}")
                        updated = True
    
    # Output for GitHub Actions
    if updated:
        print("::set-output name=has_updates::true")
        
        # Commit changes
        os.system('git config --global user.name "GitHub Actions"')
        os.system('git config --global user.email "actions@github.com"')
        os.system('git add apps/')
        os.system(f'git commit -m "chore: update app versions [skip ci]"')
        os.system('git push')
    else:
        print("::set-output name=has_updates::false")

if __name__ == "__main__":
    main()
