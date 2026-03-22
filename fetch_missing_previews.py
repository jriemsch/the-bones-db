#!/usr/bin/env python3
"""
Fetch missing Apple Music preview URLs for CHVRCHES songs
"""

import csv
import requests
import time
from urllib.parse import quote

def read_existing_results(csv_file):
    """Read existing results and find missing preview URLs"""
    missing = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row['preview_url']:
                missing.append({
                    'original_name': row['original_name'],
                    'search_name': row['search_name']
                })
    
    return missing

def search_itunes(song_name, artist="CHVRCHES"):
    """Search iTunes API for a song and return preview URL"""
    search_term = f"{song_name} {artist}"
    encoded_term = quote(search_term)
    
    url = f"https://itunes.apple.com/search?term={encoded_term}&entity=song&limit=5"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data['resultCount'] > 0:
            # Try to find best match
            for result in data['results']:
                track_name = result.get('trackName', '')
                artist_name = result.get('artistName', '')
                preview_url = result.get('previewUrl', '')
                
                if 'CHVRCHES' in artist_name.upper():
                    return {
                        'preview_url': preview_url,
                        'track_name': track_name,
                        'artist': artist_name,
                        'album': result.get('collectionName', ''),
                        'artwork_url': result.get('artworkUrl100', ''),
                        'track_id': result.get('trackId', '')
                    }
            
            # If no CHVRCHES match, return first result
            result = data['results'][0]
            return {
                'preview_url': result.get('previewUrl', ''),
                'track_name': result.get('trackName', ''),
                'artist': result.get('artistName', ''),
                'album': result.get('collectionName', ''),
                'artwork_url': result.get('artworkUrl100', ''),
                'track_id': result.get('trackId', '')
            }
        
        return None
    
    except Exception as e:
        print(f"  Error: {e}")
        return None

def update_csv(input_file, output_file, updates):
    """Update the CSV with new preview URLs"""
    rows = []
    
    # Read all existing data
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)
    
    # Update rows with new data
    for update in updates:
        for row in rows:
            if row['original_name'] == update['original_name']:
                row.update(update)
                break
    
    # Write updated data
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

def main():
    input_file = 'song_preview_urls.csv'
    
    print("📋 Reading existing results...")
    missing = read_existing_results(input_file)
    
    if not missing:
        print("✅ No missing songs! All preview URLs found.")
        return
    
    print(f"Found {len(missing)} missing songs\n")
    
    updates = []
    
    print("🔍 Fetching missing preview URLs (with delays to avoid rate limiting)...")
    for i, song in enumerate(missing, 1):
        print(f"[{i}/{len(missing)}] Searching: {song['original_name']}")
        
        # Longer delay to avoid rate limiting
        time.sleep(2)
        
        result = search_itunes(song['search_name'])
        
        if result and result['preview_url']:
            print(f"  ✅ Found: {result['track_name']} - {result['artist']}")
            updates.append({
                'original_name': song['original_name'],
                'search_name': song['search_name'],
                **result
            })
        else:
            print(f"  ❌ Still no preview found")
            updates.append({
                'original_name': song['original_name'],
                'search_name': song['search_name'],
                'preview_url': '',
                'track_name': '',
                'artist': '',
                'album': '',
                'artwork_url': '',
                'track_id': ''
            })
    
    # Update the CSV
    print(f"\n💾 Updating {input_file}...")
    update_csv(input_file, input_file, updates)
    
    # Summary
    found = sum(1 for u in updates if u['preview_url'])
    print(f"\n✨ Done!")
    print(f"   Found this time: {found}/{len(missing)}")
    print(f"   Still missing: {len(missing) - found}")

if __name__ == '__main__':
    main()
