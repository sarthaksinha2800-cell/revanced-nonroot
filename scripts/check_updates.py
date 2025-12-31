#!/usr/bin/env python3
import json
import os
import sys
import subprocess
import re
from datetime import datetime

def get_apkmirror_version(package_name):
    """
    Get latest version from APKMirror using curl (no Python dependencies)
    """
    try:
        # Using curl to fetch APKMirror data
        url = f"https://www.apkmirror.com/apk/{package_name}/"
        
        # First get the page to find the latest version
        cmd = ['curl', '-s', '-L', '-H', 'User-Agent: Mozilla/5.0', url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            # Look for version patterns in the HTML
            html = result.text
            
            # Pattern for version numbers (x.x.x or x.x.x.x)
            version_patterns = [
                r'(\d+\.\d+\.\d+(?:\.\d+)?)(?:\s*-\s*[A-Za-z]+)?\s*[Rr]elease',
                r'versionName["\']?:\s*["\']?(\d+\.\d+\.\d+(?:\.\d+)?)["\']?',
                r'(\d+\.\d+\.\d+(?:\.\d+)?)\s*[Aa]pk'
            ]
            
            for pattern in version_patterns:
                matches = re.findall(pattern, html)
                if matches:
                    # Return the first match (usually the latest)
                    return matches[0]
    
    except Exception as e:
        print(f"Error fetching version for {package_name}: {e}")
    
    return None

def check_and_update_config(config_file):
    """
    Check and update a single config file if version is empty
    """
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Only update if version is empty
        if config.get('version') == '':
            package = config.get('package', '')
            if package:
                print(f"Checking latest version for {package}...")
                
                # Extract app name for APKMirror URL
                if 'apkmirror' in config_file.lower():
                    # Try to get version from APKMirror
                    latest_version = get_apkmirror_version(package)
                    
                    if latest_version:
                        print(f"Found latest version for {package}: {latest_version}")
                        config['version'] = latest_version
                        
                        # Write updated config
                        with open(config_file, 'w') as f:
                            json.dump(config, f, indent=2)
                        return True
                    else:
                        print(f"Could not find version for {package}")
        
        return False
        
    except Exception as e:
        print(f"Error processing {config_file}: {e}")
        return False

def main():
    # Read patch-config.json to know which apps we're building
    with open('patch-config.json', 'r') as f:
        patch_config = json.load(f)
    
    updated = False
    apps_checked = set()
    
    # Check each app in patch list
    for app_config in patch_config['patch_list']:
        app_name = app_config['app_name']
        
        # Skip if we already checked this app
        if app_name in apps_checked:
            continue
        
        apps_checked.add(app_name)
        
        # Check all possible app config locations
        app_dirs = ['apps/apkmirror', 'apps/apkpure', 'apps/uptodown']
        
        for app_dir in app_dirs:
            config_file = f"{app_dir}/{app_name}.json"
            
            if os.path.exists(config_file):
                print(f"\nChecking {config_file}...")
                if check_and_update_config(config_file):
                    updated = True
                    print(f"✓ Updated {config_file}")
                else:
                    print(f"✓ No update needed for {config_file}")
                break  # Found the config, no need to check other dirs
    
    # Also check if there are any configs not in patch-config.json
    # This ensures all configs are up to date
    for app_dir in app_dirs:
        if os.path.exists(app_dir):
            for config_file in os.listdir(app_dir):
                if config_file.endswith('.json'):
                    full_path = os.path.join(app_dir, config_file)
                    if full_path not in [f"apps/{dir_}/{app}.json" for dir_ in ['apkmirror', 'apkpure', 'uptodown'] for app in apps_checked]:
                        print(f"\nChecking additional config: {full_path}...")
                        if check_and_update_config(full_path):
                            updated = True
    
    # Output for GitHub Actions
    if updated:
        print("\n" + "="*50)
        print("Updates found! Committing changes...")
        print("="*50)
        
        # Set GitHub Actions output
        with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
            print('has_updates=true', file=fh)
        
        # Commit changes
        try:
            subprocess.run(['git', 'config', '--global', 'user.name', 'GitHub Actions'], check=True)
            subprocess.run(['git', 'config', '--global', 'user.email', 'actions@github.com'], check=True)
            subprocess.run(['git', 'add', 'apps/'], check=True)
            subprocess.run(['git', 'commit', '-m', 'chore: update app versions [skip ci]'], check=True)
            subprocess.run(['git', 'push'], check=True)
        except Exception as e:
            print(f"Error committing changes: {e}")
    else:
        print("\n" + "="*50)
        print("No updates found")
        print("="*50)
        
        with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
            print('has_updates=false', file=fh)

if __name__ == "__main__":
    main()
