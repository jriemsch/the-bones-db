#!/usr/bin/env python3
import csv
from collections import Counter

with open('song_preview_urls.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    rows = list(reader)
    
    # Check for duplicate original names
    original_names = [r['original_name'] for r in rows]
    name_counts = Counter(original_names)
    duplicates = {name: count for name, count in name_counts.items() if count > 1}
    
    # Check for duplicate preview URLs (excluding empty ones)
    preview_urls = [r['preview_url'] for r in rows if r['preview_url']]
    url_counts = Counter(preview_urls)
    duplicate_urls = {url: count for url, count in url_counts.items() if count > 1}
    
    print('📊 Duplicate Analysis')
    print('=' * 60)
    print(f'Total songs: {len(rows)}')
    print(f'Unique song names: {len(name_counts)}')
    print(f'Duplicate song names: {len(duplicates)}')
    print()
    
    if duplicates:
        print('❌ Duplicate song names found:')
        for name, count in duplicates.items():
            print(f'  - "{name}" appears {count} times')
    else:
        print('✅ No duplicate song names')
    
    print()
    print(f'Total preview URLs: {len(preview_urls)}')
    print(f'Unique preview URLs: {len(url_counts)}')
    print(f'Duplicate preview URLs: {len(duplicate_urls)}')
    print()
    
    if duplicate_urls:
        print('⚠️  Same preview URL used for multiple songs:')
        for url, count in sorted(duplicate_urls.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f'  - Used {count} times')
            songs_with_url = [r['original_name'] for r in rows if r['preview_url'] == url]
            for song in songs_with_url:
                print(f'      • {song}')
            print()
    else:
        print('✅ No duplicate preview URLs')
