#!/usr/bin/env python3
"""
Fetch Apple Music preview URLs for CHVRCHES songs from iTunes Search API
"""

import csv
import requests
import time
import json
from urllib.parse import quote

def get_unique_songs(csv_file):
    """Extract unique song names from Songs.csv"""
    unique_songs = set()
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            song_name = row['Name'].strip()
            if song_name:
                # Remove remix/version indicators for search
                base_name = song_name.split(' (')[0].strip()
                unique_songs.add((song_name, base_name))
    
    return sorted(unique_songs, key=lambda x: x[0])

def search_itunes(song_name, artist="CHVRCHES"):
    """Search iTunes API for a song and return preview URL"""
    # URL encode the search term
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
                
                # Check if it's a CHVRCHES song
                if 'CHVRCHES' in artist_name.upper():
                    return {
                        'preview_url': preview_url,
                        'track_name': track_name,
                        'artist': artist_name,
                        'album': result.get('collectionName', ''),
                        'artwork_url': result.get('artworkUrl100', ''),
                        'track_id': result.get('trackId', '')
                    }
            
            # If no CHVRCHES match, return first result anyway
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
        print(f"Error searching for '{song_name}': {e}")
        return None

def main():
    csv_file = 'tables/Songs.csv'
    output_file = 'song_preview_urls.csv'
    
    print("📋 Reading Songs.csv...")
    unique_songs = get_unique_songs(csv_file)
    print(f"Found {len(unique_songs)} unique songs\n")
    
    results = []
    
    print("🔍 Fetching preview URLs from iTunes API...")
    for i, (original_name, search_name) in enumerate(unique_songs, 1):
        print(f"[{i}/{len(unique_songs)}] Searching: {original_name}")
        
        result = search_itunes(search_name)
        
        if result and result['preview_url']:
            print(f"  ✅ Found: {result['track_name']} - {result['artist']}")
            results.append({
                'original_name': original_name,
                'search_name': search_name,
                **result
            })
        else:
            print(f"  ❌ No preview found")
            results.append({
                'original_name': original_name,
                'search_name': search_name,
                'preview_url': '',
                'track_name': '',
                'artist': '',
                'album': '',
                'artwork_url': '',
                'track_id': ''
            })
        
        # Rate limiting - be nice to Apple's servers
        time.sleep(0.5)
    
    # Write results to CSV
    print(f"\n💾 Writing results to {output_file}...")
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['original_name', 'search_name', 'preview_url', 'track_name', 
                      'artist', 'album', 'artwork_url', 'track_id']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    # Summary
    found = sum(1 for r in results if r['preview_url'])
    print(f"\n✨ Done!")
    print(f"   Found previews: {found}/{len(results)}")
    print(f"   Missing: {len(results) - found}")
    print(f"   Output: {output_file}")

if __name__ == '__main__':
    main()
