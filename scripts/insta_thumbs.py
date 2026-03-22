#!/usr/bin/env python3
"""Download Instagram carousel images and create a horizontal thumbnail strip.

Usage:
  python3 insta_thumbs.py <instagram_url> --artist ARTIST --date DATE --city CITY --poster POSTER
  
Example:
  python3 insta_thumbs.py https://www.instagram.com/p/Ctoi72erxZw --artist CHVRCHES --date 2023-06-12 --city Dundee --poster Jens

Creates thumbnails sized to fit 4 across an iPhone screen (portrait mode) and
arranges them horizontally in a single image. Downloads are saved to socials/concerts/{ARTIST}/
with originals, individual thumbnails, and the final horizontal strip.
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path
from typing import List

try:
    import instaloader
except ImportError:
    print("Error: instaloader not installed. Install with: pip install instaloader", file=sys.stderr)
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow not installed. Install with: pip install Pillow", file=sys.stderr)
    sys.exit(1)


# iPhone portrait width sizing: ~390px width for modern iPhones
# 4 thumbnails across = ~97.5px each (390px / 4)
THUMB_WIDTH = 90
GAP_SIZE = 0  # No gaps between thumbnails by default
THUMB_HEIGHT = 120  # Standard height for all thumbnails


def extract_shortcode(url: str) -> str:
    """Extract Instagram shortcode from URL."""
    # Handle formats like:
    # https://www.instagram.com/p/Ctoi72erxZw/
    # https://www.instagram.com/p/Ctoi72erxZw
    parts = url.rstrip('/').split('/')
    for i, part in enumerate(parts):
        if part == 'p' and i + 1 < len(parts):
            return parts[i + 1]
    raise ValueError(f"Could not extract shortcode from URL: {url}")


def download_carousel_images(shortcode: str, output_dir: Path) -> List[Path]:
    """Download all images from an Instagram carousel post."""
    print(f"Downloading images from Instagram post: {shortcode}")
    
    # Create originals subdirectory
    originals_dir = output_dir / 'originals'
    originals_dir.mkdir(parents=True, exist_ok=True)
    
    loader = instaloader.Instaloader(
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        post_metadata_txt_pattern='',
        dirname_pattern=str(originals_dir)
    )
    
    try:
        post = instaloader.Post.from_shortcode(loader.context, shortcode)
        
        # Download the post
        loader.download_post(post, target=originals_dir)
        
        # Find all downloaded images and sort numerically by the image number in filename
        # Instagram filenames are like {shortcode}_1.jpg, {shortcode}_2.jpg, etc.
        image_files = sorted([
            f for f in originals_dir.iterdir() 
            if f.suffix.lower() in ('.jpg', '.jpeg', '.png')
        ], key=lambda f: int(f.stem.split('_')[-1]) if f.stem.split('_')[-1].isdigit() else 0)
        
        print(f"Downloaded {len(image_files)} images to {originals_dir}")
        return image_files
        
    except Exception as e:
        print(f"Error downloading Instagram post: {e}", file=sys.stderr)
        sys.exit(1)


def create_thumbnail(image_path: Path, width: int, height: int) -> Image.Image:
    """Create a thumbnail with specified dimensions, cropping to fill (no borders)."""
    with Image.open(image_path) as img:
        # Convert to RGB if needed (handle RGBA, etc.)
        if img.mode in ('RGBA', 'LA'):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        else:
            img = img.convert('RGB')
        
        # Calculate scaling to fill thumbnail dimensions (crop excess)
        img_aspect = img.width / img.height
        thumb_aspect = width / height
        
        if img_aspect > thumb_aspect:
            # Image is wider - fit to height and crop width
            new_height = height
            new_width = int(height * img_aspect)
        else:
            # Image is taller - fit to width and crop height
            new_width = width
            new_height = int(width / img_aspect)
        
        # Resize the image
        img_resized = img.resize((new_width, new_height), Image.LANCZOS)
        
        # Calculate crop coordinates to center the image
        left = (new_width - width) // 2
        top = (new_height - height) // 2
        right = left + width
        bottom = top + height
        
        # Crop to final thumbnail size
        thumb = img_resized.crop((left, top, right, bottom))
        
        return thumb


def create_horizontal_strip(image_paths: List[Path], thumb_width: int, thumb_height: int, gap: int, thumbs_dir: Path = None) -> Image.Image:
    """Create a horizontal strip of thumbnails."""
    num_images = len(image_paths)
    
    # Calculate total width: thumbnails + gaps
    total_width = (thumb_width * num_images) + (gap * (num_images - 1))
    total_height = thumb_height
    
    # Create the output canvas
    strip = Image.new('RGB', (total_width, total_height), (255, 255, 255))
    
    # Position each thumbnail
    x_position = 0
    for i, img_path in enumerate(image_paths):
        print(f"Creating thumbnail {i+1}/{num_images}...")
        thumb = create_thumbnail(img_path, thumb_width, thumb_height)
        
        # Save individual thumbnail if directory provided
        if thumbs_dir:
            thumb_filename = f"thumb_{i+1:02d}.jpg"
            thumb_path = thumbs_dir / thumb_filename
            thumb.save(thumb_path, format='JPEG', quality=90, optimize=True)
        
        strip.paste(thumb, (x_position, 0))
        x_position += thumb_width + gap
    
    return strip


def find_next_folder_number(artist_dir: Path, date: str, city: str, poster: str) -> int:
    """Find the next available folder number for the given date/city/poster combination."""
    pattern = f"{date} - {city} - {poster} "
    
    # Find all matching folders in the artist directory
    existing = [
        d.name for d in artist_dir.iterdir()
        if d.is_dir() and d.name.startswith(pattern)
    ]
    
    if not existing:
        return 1
    
    # Extract numbers from existing folders
    numbers = []
    for folder_name in existing:
        # Extract the number after the pattern
        suffix = folder_name[len(pattern):].strip()
        try:
            numbers.append(int(suffix))
        except ValueError:
            continue
    
    if not numbers:
        return 1
    
    return max(numbers) + 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Download Instagram carousel images and create horizontal thumbnail strip'
    )
    parser.add_argument('url', help='Instagram post URL (e.g., https://www.instagram.com/p/Ctoi72erxZw)')
    parser.add_argument('--artist', '-a', required=True,
                       help='Artist name (e.g., CHVRCHES)')
    parser.add_argument('--date', '-d', required=True,
                       help='Date in YYYY-MM-DD format (e.g., 2023-06-12)')
    parser.add_argument('--city', '-c', required=True,
                       help='City name (e.g., Dundee)')
    parser.add_argument('--poster', '-p', required=True,
                       help='Poster name (e.g., Jens)')
    parser.add_argument('--width', '-w', type=int, default=THUMB_WIDTH,
                       help=f'Thumbnail width in pixels (default: {THUMB_WIDTH})')
    parser.add_argument('--height', type=int, default=THUMB_HEIGHT,
                       help=f'Thumbnail height in pixels (default: {THUMB_HEIGHT})')
    parser.add_argument('--gap', '-g', type=int, default=GAP_SIZE,
                       help=f'Gap between thumbnails in pixels (default: {GAP_SIZE})')
    parser.add_argument('--quality', '-q', type=int, default=90,
                       help='JPEG quality (default: 90)')
    
    args = parser.parse_args()
    
    # Extract shortcode from URL
    try:
        shortcode = extract_shortcode(args.url)
    except ValueError as e:
        parser.error(str(e))
    
    # Determine concerts directory (relative to script location)
    script_dir = Path(__file__).parent
    concerts_dir = script_dir.parent / 'socials' / 'concerts'
    
    # Create artist subdirectory
    artist_dir = concerts_dir / args.artist
    artist_dir.mkdir(parents=True, exist_ok=True)
    
    # Find next available folder number
    folder_number = find_next_folder_number(artist_dir, args.date, args.city, args.poster)
    folder_name = f"{args.date} - {args.city} - {args.poster} {folder_number}"
    output_dir = artist_dir / folder_name
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Creating output in: {output_dir}")
    
    # Create thumbs subdirectory
    thumbs_dir = output_dir / 'thumbs'
    thumbs_dir.mkdir(parents=True, exist_ok=True)
    
    # Download images
    image_paths = download_carousel_images(shortcode, output_dir)
    
    if not image_paths:
        print("No images found in the post.", file=sys.stderr)
        sys.exit(1)
    
    # Create horizontal strip(s)
    # If more than 10 images, split into two strips
    if len(image_paths) > 10:
        print(f"Creating 2 horizontal thumbnail strips (more than 10 images)...")
        mid_point = len(image_paths) // 2
        
        # First strip with first half
        strip1 = create_horizontal_strip(image_paths[:mid_point], args.width, args.height, args.gap, thumbs_dir)
        strip1_path = output_dir / 'carousel_strip_1.jpg'
        strip1.save(strip1_path, format='JPEG', quality=args.quality, optimize=True)
        
        # Second strip with second half
        strip2 = create_horizontal_strip(image_paths[mid_point:], args.width, args.height, args.gap, thumbs_dir)
        strip2_path = output_dir / 'carousel_strip_2.jpg'
        strip2.save(strip2_path, format='JPEG', quality=args.quality, optimize=True)
        
        total_width1 = (args.width * mid_point) + (args.gap * (mid_point - 1))
        total_width2 = (args.width * (len(image_paths) - mid_point)) + (args.gap * (len(image_paths) - mid_point - 1))
        print(f"\nSuccess! Created files in {output_dir}/")
        print(f"  - Original images: {output_dir / 'originals'}/")
        print(f"  - Individual thumbnails: {output_dir / 'thumbs'}/")
        print(f"  - Horizontal strip 1: {strip1_path}")
        print(f"    - {mid_point} images, strip size: {total_width1}x{args.height}px")
        print(f"  - Horizontal strip 2: {strip2_path}")
        print(f"    - {len(image_paths) - mid_point} images, strip size: {total_width2}x{args.height}px")
    else:
        print(f"Creating horizontal thumbnail strip...")
        strip = create_horizontal_strip(image_paths, args.width, args.height, args.gap, thumbs_dir)
        
        # Save the result
        strip_path = output_dir / 'carousel_strip.jpg'
        strip.save(strip_path, format='JPEG', quality=args.quality, optimize=True)
        
        total_width = (args.width * len(image_paths)) + (args.gap * (len(image_paths) - 1))
        print(f"\nSuccess! Created files in {output_dir}/")
        print(f"  - Original images: {output_dir / 'originals'}/")
        print(f"  - Individual thumbnails: {output_dir / 'thumbs'}/")
        print(f"  - Horizontal strip: {strip_path}")
        print(f"  - {len(image_paths)} images ({args.width}x{args.height}px each)")
        print(f"  - Strip size: {total_width}x{args.height}px")


if __name__ == '__main__':
    main()
