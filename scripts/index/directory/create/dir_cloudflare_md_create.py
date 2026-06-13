#!/usr/bin/env python3
"""Create KB structure for Cloudflare applications from bookmarks."""

import re
from pathlib import Path
from html import unescape
from datetime import datetime

def parse_cloudflare_apps(html_path):
    """Extract Cloudflare application bookmarks."""
    content = Path(html_path).read_text(encoding='utf-8')
    
    # Find Cloudflare section
    pattern = r'<H3[^>]*>Cloudflarepages</H3>.*?<DL><p>(.*?)</DL>'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        return []
    
    section = match.group(1)
    
    # Extract all links
    link_pattern = r'<A HREF="([^"]+)"[^>]*>([^<]+)</A>'
    links = re.findall(link_pattern, section)
    
    apps = []
    for url, title in links:
        # Extract app name from URL
        app_match = re.search(r'/pages/view/([^/?]+)', url)
        if app_match:
            app_name = app_match.group(1)
            apps.append({
                'name': app_name,
                'title': unescape(title.strip()),
                'url': url,
                'dashboard_url': url
            })
        # Also check for workers
        worker_match = re.search(r'/workers/services/view/([^/]+)', url)
        if worker_match:
            app_name = worker_match.group(1)
            apps.append({
                'name': app_name,
                'title': unescape(title.strip()),
                'url': url,
                'dashboard_url': url,
                'type': 'worker'
            })
    
    return apps

def slugify(name):
    """Convert name to folder-friendly slug."""
    # Replace hyphens and underscores with spaces, then title case
    name = name.replace('-', ' ').replace('_', ' ')
    # Keep it simple for folder names
    return name

def create_app_page(app, folder_path):
    """Create documentation page for a Cloudflare application."""
    app_name_display = slugify(app['name']).title()
    app_type = app.get('type', 'pages')
    
    # Determine category based on name
    category = 'infrastructure'
    if 'client' in app['name'].lower() or 'portal' in app['name'].lower():
        category = 'client'
    elif 'personal' in app['name'].lower() or 'portfolio' in app['name'].lower():
        category = 'personal'
    
    content = f"""---
title: "{app_name_display} — Cloudflare {app_type.title()}"
slug: {app['name']}
realm: 2_QsKb
qi_decimal: 70.20.{app['name'][:2].upper()}-01
date: {datetime.now().strftime('%Y-%m-%d')}
category: {category}
life_stage: early-30s
privacy: internal
status: active
tags:
  - cloudflare
  - {app_type}
  - infrastructure
description: >
  Documentation and configuration for {app_name_display} Cloudflare {app_type} application.
permalink: /2_QsKb/2.70_TECH/bookmarks/Cloudflare/{app['name']}/README.md
meta:
  platform: cloudflare
  service_type: {app_type}
  dashboard_url: {app['dashboard_url']}
---

# {app_name_display}

**Type:** Cloudflare {app_type.title()}  
**Application Name:** `{app['name']}`

## Quick Links

- [Cloudflare Dashboard]({app['dashboard_url']})

## Overview

{app_name_display} is deployed on Cloudflare {app_type.title()}.

## Configuration

_Add configuration details, environment variables, and deployment settings here._

## Deployment

_Add deployment instructions and CI/CD configuration here._

## Monitoring

_Add monitoring, logging, and analytics information here._

## Notes

_Add any additional notes, troubleshooting tips, or important information here._

---

**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}
"""
    
    readme_path = folder_path / "README.md"
    readme_path.write_text(content, encoding='utf-8')
    return readme_path

def main():
    """Main entry point."""
    import sys
    
    bookmarks_path = sys.argv[1] if len(sys.argv) > 1 else r'c:\Users\codyr\Downloads\bookmarks_11_9_25.html'
    kb_base = Path('2_QsKb/2.70_TECH/bookmarks')
    
    # Create bookmarks folder structure
    bookmarks_folder = kb_base
    cloudflare_folder = bookmarks_folder / 'Cloudflare'
    
    bookmarks_folder.mkdir(parents=True, exist_ok=True)
    cloudflare_folder.mkdir(parents=True, exist_ok=True)
    
    # Create index file for bookmarks
    bookmarks_index = bookmarks_folder / '_bookmarks.md'
    bookmarks_index.write_text(f"""---
title: Bookmarks
slug: bookmarks
realm: 2_QsKb
qi_decimal: 70.20.00-00
date: {datetime.now().strftime('%Y-%m-%d')}
category: infrastructure
life_stage: early-30s
privacy: internal
status: active
tags:
  - bookmarks
  - infrastructure
description: >
  Collection of bookmarks and links for services, applications, and resources.
permalink: /2_QsKb/2.70_TECH/bookmarks/_bookmarks.md
---

# Bookmarks

Collection of bookmarks and links organized by service provider and category.

## Cloudflare

See [[Cloudflare/_Cloudflare|Cloudflare Applications]] for all Cloudflare Pages and Workers.

---

**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}
""", encoding='utf-8')
    
    # Parse Cloudflare apps
    print(f"Parsing Cloudflare applications from: {bookmarks_path}")
    apps = parse_cloudflare_apps(bookmarks_path)
    
    print(f"Found {len(apps)} Cloudflare applications")
    print()
    
    # Create Cloudflare index
    cloudflare_index = cloudflare_folder / '_Cloudflare.md'
    cloudflare_index.write_text(f"""---
title: Cloudflare Applications
slug: cloudflare-applications
realm: 2_QsKb
qi_decimal: 70.20.10-00
date: {datetime.now().strftime('%Y-%m-%d')}
category: infrastructure
life_stage: early-30s
privacy: internal
status: active
tags:
  - cloudflare
  - infrastructure
  - pages
  - workers
description: >
  Documentation for all Cloudflare Pages and Workers applications.
permalink: /2_QsKb/2.70_TECH/bookmarks/Cloudflare/_Cloudflare.md
---

# Cloudflare Applications

Documentation and configuration for all Cloudflare Pages and Workers applications.

## Applications ({len(apps)} total)

""", encoding='utf-8')
    
    # Create folder and page for each app
    created = []
    for app in apps:
        app_folder = cloudflare_folder / app['name']
        app_folder.mkdir(exist_ok=True)
        
        readme_path = create_app_page(app, app_folder)
        created.append(app)
        
        # Add to index
        app_name_display = slugify(app['name']).title()
        app_type = app.get('type', 'pages')
        with open(cloudflare_index, 'a', encoding='utf-8') as f:
            f.write(f"- [[{app['name']}/README|{app_name_display}]] ({app_type})\n")
        
        print(f"  ✅ Created: {app['name']}")
    
    # Finalize index
    with open(cloudflare_index, 'a', encoding='utf-8') as f:
        f.write(f"""
---

**Total Applications:** {len(apps)}  
**Last Updated:** {datetime.now().strftime('%Y-%m-%d')}
""")
    
    print()
    print(f"✅ Created {len(created)} Cloudflare application documentation pages")
    print(f"   Location: {cloudflare_folder}")
    print()
    print("📝 Next steps:")
    print("   - Review and update each application's README.md")
    print("   - Add configuration details, deployment info, and notes")

if __name__ == '__main__':
    main()

