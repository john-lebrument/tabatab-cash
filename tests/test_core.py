import sys
import unittest
from unittest.mock import patch
from pathlib import Path
from PIL import Image

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.file_ops import is_image_file, move_file, copy_file, crop_image
from src.config import ConfigManager


class TestCoreFeatures(unittest.TestCase):

    def setUp(self):
        self.test_dir = PROJECT_ROOT / "tests" / "temp_test_dir"
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.settings_patch = patch('src.config.get_settings_path', return_value=self.test_dir / 'settings.json')
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)
        self.dir_a = self.test_dir / "folder_a"
        self.dir_b = self.test_dir / "folder_b"
        self.dir_a.mkdir(exist_ok=True)
        self.dir_b.mkdir(exist_ok=True)

        # Create a test image: 800x600 red image
        self.test_img_path = self.dir_a / "test_photo.jpg"
        img = Image.new("RGB", (800, 600), color=(255, 0, 0))
        img.save(self.test_img_path, format="JPEG")

    def tearDown(self):
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_is_image_file(self):
        self.assertTrue(is_image_file("photo.jpg"))
        self.assertTrue(is_image_file("photo.PNG"))
        self.assertTrue(is_image_file("photo.webp"))
        self.assertFalse(is_image_file("document.pdf"))
        self.assertFalse(is_image_file("script.py"))

    def test_copy_file(self):
        dest = copy_file(self.test_img_path, self.dir_b)
        self.assertTrue(dest.exists())
        self.assertTrue(self.test_img_path.exists())  # Source still exists
        self.assertEqual(dest.name, "test_photo.jpg")

    def test_move_file(self):
        dest = move_file(self.test_img_path, self.dir_b)
        self.assertTrue(dest.exists())
        self.assertFalse(self.test_img_path.exists())  # Source moved
        self.assertEqual(dest.name, "test_photo.jpg")

    def test_crop_image(self):
        # Crop 800x600 image from (100, 100) to (500, 400) -> 400x300
        cropped_path = crop_image(self.test_img_path, (100, 100, 500, 400), overwrite=False)
        self.assertTrue(cropped_path.exists())
        self.assertEqual(cropped_path.name, "test_photo_crop.jpg")

        with Image.open(cropped_path) as img:
            self.assertEqual(img.size, (400, 300))

    def test_copy_file_same_folder_renaming(self):
        # When copying into the same folder, it should create 'test_photo - Copie.jpg'
        copy1 = copy_file(self.test_img_path, self.dir_a)
        self.assertTrue(copy1.exists())
        self.assertEqual(copy1.name, "test_photo - Copie.jpg")

        # Second copy should create 'test_photo - Copie (2).jpg'
        copy2 = copy_file(self.test_img_path, self.dir_a)
        self.assertTrue(copy2.exists())
        self.assertEqual(copy2.name, "test_photo - Copie (2).jpg")

    def test_convert_image_format_keep_both(self):
        from src.utils.file_ops import convert_image_format
        png_path = convert_image_format(self.test_img_path, ".png", overwrite=False)
        self.assertTrue(png_path.exists())
        self.assertTrue(self.test_img_path.exists())
        self.assertEqual(png_path.suffix.lower(), ".png")

        webp_path = convert_image_format(self.test_img_path, ".webp", overwrite=False)
        self.assertTrue(webp_path.exists())
        self.assertEqual(webp_path.suffix.lower(), ".webp")

        bmp_path = convert_image_format(self.test_img_path, ".bmp", overwrite=False)
        self.assertTrue(bmp_path.exists())
        self.assertEqual(bmp_path.suffix.lower(), ".bmp")

    def test_convert_image_format_overwrite(self):
        from src.utils.file_ops import convert_image_format
        # Create a dedicated temp image to be replaced
        to_replace = self.dir_b / "replace_me.jpg"
        img = Image.new("RGB", (100, 100), color=(0, 255, 0))
        img.save(to_replace, format="JPEG")

        dest_png = convert_image_format(to_replace, ".png", overwrite=True)
        self.assertTrue(dest_png.exists())
        self.assertFalse(to_replace.exists())  # Original was replaced/deleted

    def test_config_manager(self):
        config = ConfigManager()
        config.set("thumbnail_size", 180)
        self.assertEqual(config.get("thumbnail_size"), 180)


if __name__ == "__main__":
    unittest.main()
