#!/usr/bin/env python3
"""
Icon Generation Script for Vybe
Converts the SVG icon to various formats needed by the application.
"""

import subprocess
import sys
import os
from pathlib import Path

# Configuration for icon paths - makes paths configurable instead of hardcoded
class IconConfig:
    """Configuration class for icon paths"""
    def __init__(self, base_dir: Path | None = None):
        self.base_dir = base_dir or Path(__file__).parent
        
        # Default paths - can be overridden via environment variables
        self.svg_path = Path(os.getenv('VYBE_SVG_PATH', 
                                      str(self.base_dir / "vybe-desktop" / "src-tauri" / "icons" / "icon.svg")))
        self.img_dir = Path(os.getenv('VYBE_IMG_DIR', 
                                     str(self.base_dir / "vybe_app" / "static" / "img")))
        self.favicon_path = Path(os.getenv('VYBE_FAVICON_PATH',
                                          str(self.base_dir / "vybe_app" / "static" / "favicon.ico")))
        self.assets_dir = Path(os.getenv('VYBE_ASSETS_DIR',
                                        str(self.base_dir / "assets")))

def check_dependencies():
    """Check if required dependencies are available"""
    try:
        from PIL import Image, ImageDraw
        return True
    except ImportError:
        print("Pillow not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
        try:
            from PIL import Image, ImageDraw
            return True
        except ImportError:
            return False

def create_simple_icon():
    """Create a simple icon when SVG conversion fails"""
    from PIL import Image, ImageDraw
    
    # Create a 256x256 icon with Vybe branding
    size = 256
    img = Image.new('RGBA', (size, size))
    draw = ImageDraw.Draw(img)
    
    # Background circle with gradient effect
    center = size // 2
    radius = size // 2 - 10
    
    # Create a circular background
    for i in range(radius, 0, -2):
        alpha = int(255 * (radius - i) / radius)
        color = (138, 43, 226, alpha)  # Purple gradient
        draw.ellipse([center-i, center-i, center+i, center+i], fill=color)
    
    # Draw the V shape
    v_width = 8
    v_height = 80
    v_top_y = center - v_height // 2
    v_bottom_y = center + v_height // 2
    v_left_x = center - 40
    v_right_x = center + 40
    
    # Left line of V
    draw.line([(v_left_x, v_top_y), (center, v_bottom_y)], 
              fill=(255, 255, 255, 255), width=v_width)
    # Right line of V
    draw.line([(center, v_bottom_y), (v_right_x, v_top_y)], 
              fill=(255, 255, 255, 255), width=v_width)
    
    # Add accent dots
    dot_radius = 6
    draw.ellipse([center-60-dot_radius, center-80-dot_radius, 
                  center-60+dot_radius, center-80+dot_radius], 
                 fill=(255, 255, 255, 200))
    draw.ellipse([center+60-dot_radius, center-80-dot_radius, 
                  center+60+dot_radius, center-80+dot_radius], 
                 fill=(255, 255, 255, 200))
    
    return img

def generate_icons(config: IconConfig | None = None):
    """Generate icon files from SVG or create simple fallback"""
    if config is None:
        config = IconConfig()
        
    config.img_dir.mkdir(parents=True, exist_ok=True)
    
    if not check_dependencies():
        print("Could not install required dependencies")
        return False
    
    from PIL import Image
    
    # Try to use SVG conversion if available
    icon_img = None
    try:
        # Try to use cairosvg if available
        try:
            import cairosvg
            from io import BytesIO
            
            svg_data = config.svg_path.read_text()
            png_data = cairosvg.svg2png(bytestring=svg_data.encode('utf-8'), 
                                       output_width=256, output_height=256)
            if png_data:
                icon_img = Image.open(BytesIO(png_data))
                print("✅ Successfully converted SVG using cairosvg")
            else:
                raise Exception("SVG conversion returned no data")
            
        except ImportError:
            print("cairosvg not available, creating simple icon...")
            icon_img = create_simple_icon()
            
    except Exception as e:
        print(f"SVG conversion failed: {e}")
        print("Creating simple icon...")
        icon_img = create_simple_icon()
    
    if icon_img is None:
        print("Failed to create icon")
        return False
    
    # Save as ICO with multiple sizes
    try:
        ico_path = config.img_dir / "logo.ico"
        
        # Create different sizes for ICO
        sizes = [16, 32, 48, 64, 128, 256]
        icon_images = []
        
        for size in sizes:
            resized = icon_img.resize((size, size), Image.Resampling.LANCZOS)
            icon_images.append(resized)
        
        # Save as ICO
        icon_images[0].save(
            ico_path,
            format='ICO',
            sizes=[(img.width, img.height) for img in icon_images],
            append_images=icon_images[1:]
        )
        
        print(f"✅ Created {ico_path}")
        
        # Also save as PNG for web use
        png_path = config.img_dir / "logo.png"
        icon_img.save(png_path, format='PNG')
        print(f"✅ Created {png_path}")
        
        # Create favicon.ico in static root
        if not config.favicon_path.exists():
            icon_images[0].save(
                config.favicon_path,
                format='ICO',
                sizes=[(img.width, img.height) for img in icon_images],
                append_images=icon_images[1:]
            )
            print(f"✅ Created {config.favicon_path}")
        
        return True
        
    except Exception as e:
        print(f"Error saving icon: {e}")
        return False

if __name__ == "__main__":
    print("Generating Vybe icons...")
    if generate_icons():
        print("✅ Icon generation completed successfully!")
    else:
        print("❌ Icon generation failed!")
        sys.exit(1)
