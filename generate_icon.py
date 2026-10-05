from pathlib import Path
from PIL import Image, ImageDraw

res_dir = Path(__file__).resolve().parent / "resources"
res_dir.mkdir(parents=True, exist_ok=True)

# Generate a 256x256 modern icon
size = 256
img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Outer rounded rectangle (dark slate / deep blue)
draw.rounded_rectangle([8, 8, size - 8, size - 8], radius=40, fill=(28, 32, 40, 255), outline=(0, 120, 212, 255), width=6)

# Sun / Moon circle
draw.ellipse([160, 48, 204, 92], fill=(255, 193, 7, 255))

# Mountain / Landscape triangles
draw.polygon([(40, 190), (105, 105), (170, 190)], fill=(0, 120, 212, 255))
draw.polygon([(125, 190), (175, 125), (225, 190)], fill=(76, 194, 255, 255))

# Tab indication bar at top
draw.rounded_rectangle([32, 24, 110, 42], radius=6, fill=(0, 120, 212, 255))
draw.rounded_rectangle([118, 24, 190, 42], radius=6, fill=(60, 65, 75, 255))

png_path = res_dir / "app_icon.png"
ico_path = res_dir / "app_icon.ico"

img.save(png_path, format="PNG")
img.save(ico_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(f"Generated {png_path} and {ico_path}")
