#!/usr/bin/env python3
"""
Substack RSS Feed Archiver

Archives Substack RSS feed articles to a JSON file for unlimited timeline scrollback.
Run this periodically (e.g., daily via cron/GitHub Actions) to capture new articles.
"""

import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
import urllib.request
import sys

# Configuration
SUBSTACK_FEED_URL = "https://themerchbooth.substack.com/feed"
ARCHIVE_FILE = Path(__file__).parent / "tables" / "Substack_Archive.json"


def fetch_rss_feed(url):
    """Fetch RSS feed from URL."""
    req = urllib.request.Request(
        url,
        headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
    )
    with urllib.request.urlopen(req) as response:
        return response.read().decode('utf-8')


def parse_rss_item(item, namespaces):
    """Parse a single RSS item into our archive format."""
    def get_text(element, tag, ns=None):
        child = element.find(tag, ns) if ns else element.find(tag)
        return child.text if child is not None and child.text else ""
    
    # Extract data
    article = {
        "guid": get_text(item, "guid"),
        "title": get_text(item, "title"),
        "link": get_text(item, "link"),
        "pubDate": get_text(item, "pubDate"),
        "creator": get_text(item, "{http://purl.org/dc/elements/1.1/}creator"),
        "description": get_text(item, "description"),
        "contentEncoded": get_text(item, "{http://purl.org/rss/1.0/modules/content/}encoded"),
        "categories": [cat.text for cat in item.findall("category") if cat.text],
        "archivedAt": datetime.utcnow().isoformat() + "Z"
    }
    
    # Handle enclosure (media)
    enclosure = item.find("enclosure")
    if enclosure is not None:
        article["enclosure"] = {
            "url": enclosure.get("url", ""),
            "type": enclosure.get("type", ""),
            "length": int(enclosure.get("length", "0"))
        }
    
    return article


def load_archive():
    """Load existing archive or create new one."""
    if ARCHIVE_FILE.exists():
        with open(ARCHIVE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "channel": {
            "title": "The Merch Booth Archive",
            "link": "https://themerchbooth.substack.com",
            "description": "Archived articles from The Merch Booth Substack"
        },
        "items": []
    }


def save_archive(archive):
    """Save archive to file."""
    ARCHIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(ARCHIVE_FILE, 'w', encoding='utf-8') as f:
        json.dump(archive, f, indent=2, ensure_ascii=False)


def main():
    print(f"📡 Fetching RSS feed: {SUBSTACK_FEED_URL}")
    
    try:
        # Fetch current RSS feed
        rss_content = fetch_rss_feed(SUBSTACK_FEED_URL)
        
        # Parse RSS
        root = ET.fromstring(rss_content)
        namespaces = {
            'content': 'http://purl.org/rss/1.0/modules/content/',
            'dc': 'http://purl.org/dc/elements/1.1/'
        }
        
        # Load existing archive
        print(f"📂 Loading archive: {ARCHIVE_FILE}")
        archive = load_archive()
        
        # Get existing GUIDs for deduplication
        existing_guids = {item["guid"] for item in archive["items"]}
        
        # Parse new items
        new_items = []
        for item in root.findall(".//item"):
            article = parse_rss_item(item, namespaces)
            
            if article["guid"] and article["guid"] not in existing_guids:
                new_items.append(article)
                existing_guids.add(article["guid"])
        
        if new_items:
            print(f"✨ Found {len(new_items)} new article(s)")
            
            # Add new items to archive
            archive["items"].extend(new_items)
            
            # Sort by publication date (newest first)
            archive["items"].sort(
                key=lambda x: x.get("pubDate", ""),
                reverse=True
            )
            
            # Save archive
            save_archive(archive)
            print(f"💾 Archive updated: {ARCHIVE_FILE}")
            print(f"📊 Total archived articles: {len(archive['items'])}")
            
            # Print new articles
            for item in new_items:
                print(f"   + {item['title']}")
        else:
            print(f"✓ No new articles (archive has {len(archive['items'])} total)")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
