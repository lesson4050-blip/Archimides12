import sys
from PIL import Image

def process_logo(input_path, output_path):
    try:
        with Image.open(input_path) as img:
            print(f"Original size: {img.size}, mode: {img.mode}")
            
            # Since the layout uses it as an icon, we can resize it to something manageable like 128x128 
            # preserving aspect ratio 
            img.thumbnail((128, 128), Image.Resampling.LANCZOS)
            
            # Save optimized
            img.save(output_path, "PNG", optimize=True)
            print(f"Saved optimized logo to {output_path}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    process_logo("d:/Cosmo/logo.png", "d:/Cosmo/frontend/public/logo-optimized.png")
