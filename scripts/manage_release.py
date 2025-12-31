#!/usr/bin/env python3
import os
import glob
import json
from datetime import datetime
import re

def generate_release_body():
    """Generate markdown for release notes"""
    try:
        with open('patch-config.json', 'r') as f:
            config = json.load(f)
        
        body = "# ReVanced Patched APKs\n\n"
        body += "## 📦 Available Apps\n\n"
        
        for app in config.get('patch_list', []):
            app_name = app.get('app_name', 'Unknown')
            source = app.get('source', '')
            
            # Try to extract version from URL
            version_match = re.search(r'(\d+\.\d+\.\d+)', source)
            version = version_match.group(1) if version_match else "Unknown"
            
            body += f"### {app_name.replace('_', ' ').title()}\n"
            body += f"- **Version:** `{version}`\n"
            body += f"- **Last Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}\n\n"
        
        body += "---\n\n"
        body += "## 🔧 Build Information\n\n"
        body += "- **Build Date:** " + datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC') + "\n"
        body += "- **Source:** [ReVanced Patches](https://github.com/revanced/revanced-patches)\n"
        body += "- **Auto-built:** Every 6 hours or on demand\n"
        body += "\n## ⚠️ Disclaimer\n"
        body += "These APKs are built automatically. Use at your own risk.\n"
        
        return body
    except Exception as e:
        print(f"Error generating release body: {e}")
        return "ReVanced Patched APKs - Auto-built release"

def update_release_info():
    """Update release information file"""
    release_info = {
        "last_updated": datetime.now().isoformat(),
        "build_count": 0
    }
    
    # Try to read existing info
    try:
        if os.path.exists('release-info.json'):
            with open('release-info.json', 'r') as f:
                existing = json.load(f)
                release_info["build_count"] = existing.get("build_count", 0) + 1
    except:
        pass
    
    # Write updated info
    with open('release-info.json', 'w') as f:
        json.dump(release_info, f, indent=2)
    
    return release_info

if __name__ == "__main__":
    # This will be called after successful build
    update_release_info()
    print("Release info updated")
