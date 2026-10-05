import os
import shutil
import tempfile
import uuid
import re
from pathlib import Path
from typing import Optional
from PIL import Image, ImageOps
from PyQt6.QtCore import QFile

# Session undo cache also works on Windows volumes where Qt cannot return the
# recycled file's path, or where a network share has no recycle bin.
_undo_directory = tempfile.TemporaryDirectory(prefix='xnviewtab-undo-')
_deleted_images = []


def restore_last_deleted():
    if not _deleted_images:
        return None
    original, backup, recycled = _deleted_images[-1]
    if original.exists():
        raise OSError("Le nom d'origine est déjà utilisé ; restauration annulée.")
    original.parent.mkdir(parents=True, exist_ok=True)
    if recycled is not None and recycled.is_file():
        shutil.move(str(recycled), str(original))
        # Windows pairs the recycled content ($R) with its metadata ($I).
        if recycled.name.startswith('$R') and recycled.parent.parent.name.casefold() == '$recycle.bin':
            try:
                recycled.with_name('$I' + recycled.name[2:]).unlink(missing_ok=True)
            except OSError:
                pass
    else:
        shutil.copy2(backup, original)
    backup.unlink(missing_ok=True)
    _deleted_images.pop()
    return str(original)

SUPPORTED_IMAGE_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp",
    ".tiff", ".tif", ".ico", ".jfif", ".avif"
}

SUPPORTED_VIDEO_EXTENSIONS = {'.mp4', '.m4v', '.mkv', '.avi', '.mov', '.wmv', '.webm', '.mpg', '.mpeg', '.mts', '.m2ts', '.3gp', '.flv'}


def is_video_file(path):
    return Path(path).suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS


def is_media_file(path):
    return is_image_file(path) or is_video_file(path)


def is_image_file(path: Path | str) -> bool:
    """Checks whether the file has a supported image extension."""
    return Path(path).suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS


def trash_image(path: str | Path):
    """Recycle when possible, otherwise delete with a session undo backup."""
    path = Path(path).absolute()
    if not path.is_file() or not is_media_file(path):
        raise OSError("Ce fichier image n'existe plus.")
    file = QFile(str(path))
    backup = Path(_undo_directory.name) / uuid.uuid4().hex
    shutil.copy2(path, backup)
    if not file.moveToTrash():
        try:
            path.unlink()
        except OSError:
            backup.unlink(missing_ok=True)
            raise
        recycled_name = None
    else:
        recycled_name = file.fileName()
    recycled = Path(recycled_name) if isinstance(recycled_name, str) and recycled_name else None
    if recycled == path:
        recycled = None
    _deleted_images.append((path, backup, recycled))


def get_unique_destination_path(target_folder: Path, filename: str) -> Path:
    """Returns a unique file path in target_folder, appending _1, _2, etc. if needed."""
    dest = target_folder / filename
    if not dest.exists():
        return dest

    base = dest.stem
    suffix = dest.suffix
    counter = 1
    while dest.exists():
        dest = target_folder / f"{base}_{counter}{suffix}"
        counter += 1
    return dest


def get_copy_destination_path(target_folder: Path, source_path: Path) -> Path:
    """Returns a copy path formatted like Windows Explorer (e.g. 'Photo - Copie.jpg', 'Photo - Copie (2).jpg')."""
    base = source_path.stem
    suffix = source_path.suffix
    dest = target_folder / f"{base} - Copie{suffix}"
    if not dest.exists():
        return dest

    counter = 2
    while dest.exists():
        dest = target_folder / f"{base} - Copie ({counter}){suffix}"
        counter += 1
    return dest


def move_file(source_path: str | Path, target_folder: str | Path, overwrite: bool = False) -> Path:
    """Moves a file from source_path to target_folder."""
    source = Path(source_path)
    target_dir = Path(target_folder)
    if source.is_dir():
        validate_folder_transfer(source, target_dir)
        if source.parent.resolve() == target_dir.resolve():
            return source
    target_dir.mkdir(parents=True, exist_ok=True)

    if overwrite:
        dest = target_dir / source.name
    else:
        dest = get_unique_destination_path(target_dir, source.name)

    if source.is_dir() and dest.exists():
        raise FileExistsError('Le dossier de destination existe déjà.')
    shutil.move(str(source), str(dest))
    return dest


def copy_file(source_path: str | Path, target_folder: str | Path, overwrite: bool = False) -> Path:
    """Copies a file from source_path to target_folder, naming duplicates with '- Copie'."""
    source = Path(source_path)
    target_dir = Path(target_folder)
    if source.is_dir():
        validate_folder_transfer(source, target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    if overwrite:
        dest = target_dir / source.name
    elif source.parent.resolve() == target_dir.resolve():
        dest = get_copy_destination_path(target_dir, source)
    else:
        dest = get_unique_destination_path(target_dir, source.name)

    if source.is_dir():
        shutil.copytree(source, dest, symlinks=True)
    else:
        shutil.copy2(str(source), str(dest))
    return dest


def validate_folder_transfer(source, target):
    source, target = Path(source).resolve(), Path(target).resolve()
    if source == Path(source.anchor):
        raise OSError('Un lecteur ne peut pas être déplacé ou copié comme un dossier.')
    if target == source or source in target.parents:
        raise OSError('Un dossier ne peut pas être déposé dans lui-même ou dans un de ses sous-dossiers.')


def rename_folder(path, name):
    source = Path(path).absolute()
    name = name.strip()
    if (not name or name in ('.', '..') or name.endswith('.')
            or re.search(r'[<>:"/\\|?*\x00-\x1f]', name)
            or re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', name)):
        raise ValueError('Ce nom de dossier est invalide.')
    if not source.is_dir() or source == Path(source.anchor):
        raise OSError('Ce dossier ne peut pas être renommé.')
    destination = source.with_name(name)
    if destination.exists() and destination != source:
        raise FileExistsError('Un dossier ou un fichier porte déjà ce nom.')
    if source.name != destination.name:
        source.rename(destination)
    return str(destination)


def convert_image_format(
    source_path: str | Path,
    target_ext: str,
    overwrite: bool = False
) -> Path:
    """
    Converts an image to a target extension (.jpg, .png, .webp, .bmp).
    If overwrite is True, replaces or removes original.
    If overwrite is False, preserves original and creates a new converted file.
    """
    src = Path(source_path)
    target_ext = target_ext.lower()
    if not target_ext.startswith("."):
        target_ext = f".{target_ext}"

    target_dir = src.parent

    if overwrite and src.suffix.lower() == target_ext:
        dest = src
    else:
        dest = get_unique_destination_path(target_dir, f"{src.stem}{target_ext}")

    with Image.open(src) as img:
        transposed = ImageOps.exif_transpose(img)
        save_format = {
            ".jpg": "JPEG",
            ".jpeg": "JPEG",
            ".png": "PNG",
            ".webp": "WEBP",
            ".bmp": "BMP",
        }.get(target_ext, "PNG")

        save_kwargs = {}
        img_to_save = transposed

        if save_format == "JPEG":
            save_kwargs["quality"] = 95
            save_kwargs["subsampling"] = 0
            # Handle alpha transparency by flattening onto white
            if img_to_save.mode in ("RGBA", "LA") or (
                img_to_save.mode == "P" and "transparency" in img_to_save.info
            ):
                rgba = img_to_save.convert("RGBA")
                bg = Image.new("RGB", rgba.size, (255, 255, 255))
                bg.paste(rgba, mask=rgba.split()[3])
                img_to_save = bg
            elif img_to_save.mode != "RGB":
                img_to_save = img_to_save.convert("RGB")
        elif save_format == "BMP":
            if img_to_save.mode not in ("RGB", "L"):
                img_to_save = img_to_save.convert("RGB")
        elif save_format == "WEBP":
            save_kwargs["quality"] = 95
            if img_to_save.mode not in ("RGB", "RGBA"):
                img_to_save = img_to_save.convert("RGBA")
        elif save_format == "PNG":
            save_kwargs["compress_level"] = 6

        img_to_save.load()

    # Close the source on Windows before deleting it; publish only a complete
    # conversion and never overwrite a different image with the same stem.
    with tempfile.NamedTemporaryFile(prefix='.xnviewtab-convert-', suffix=target_ext,
                                     dir=target_dir, delete=False) as temporary:
        temp_dest = Path(temporary.name)
    try:
        img_to_save.save(temp_dest, format=save_format, **save_kwargs)
        temp_dest.replace(dest)
        if overwrite and src.resolve() != dest.resolve():
            src.unlink()
    finally:
        temp_dest.unlink(missing_ok=True)

    return dest


def rename_images(paths, first_name):
    """Rename in supplied display order, preserving extensions and existing files."""
    sources = [Path(p) for p in paths]
    name = first_name.strip()
    if not name or name.endswith('.') or re.search(r'[<>:"/\\|?*\x00-\x1f]', name):
        raise ValueError('Saisissez un nom valide, sans extension ni caractère interdit.')
    if re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', name):
        raise ValueError('Ce nom est réservé par Windows.')
    match = re.fullmatch(r'(.*?)(\d+)', name)
    plan = []
    for index, source in enumerate(sources):
        if not source.is_file() or not is_media_file(source):
            raise ValueError(f'Image introuvable : {source.name}')
        if len(sources) == 1:
            stem = name
        elif match:
            stem = match[1] + str(int(match[2]) + index).zfill(max(3, len(match[2])))
        else:
            stem = f'{name} {index + 1:03d}'
        destination = source.with_name(stem + source.suffix)
        if destination.exists() and destination != source:
            raise FileExistsError(f'Le fichier « {destination.name} » existe déjà. Aucun fichier renommé.')
        plan.append((source, destination))
    completed = []
    try:
        for source, destination in plan:
            if source.name != destination.name:
                source.rename(destination)
                completed.append((source, destination))
    except OSError as error:
        failures = []
        for source, destination in reversed(completed):
            try:
                destination.rename(source)
            except OSError:
                failures.append(str(destination))
        if failures:
            raise OSError(f'{error}\nFichiers restés renommés : ' + ', '.join(failures)) from error
        raise
    return [(str(source), str(destination)) for source, destination in plan]


def crop_image(
    image_path: str | Path,
    crop_box: tuple[int, int, int, int],
    destination_path: Optional[str | Path] = None,
    overwrite: bool = False,
    rotation_degrees: int = 0,
) -> Path:
    """
    Crops the image defined by crop_box (left, top, right, bottom) in original image pixels.
    If destination_path is None and not overwrite, generates a new filename with '_crop'.
    """
    src = Path(image_path)
    if destination_path is None:
        if overwrite:
            dest = src
        else:
            dest = get_unique_destination_path(src.parent, f"{src.stem}_crop{src.suffix}")
    else:
        dest = Path(destination_path)

    # Open image, respect EXIF orientation
    with Image.open(src) as img:
        transposed = ImageOps.exif_transpose(img)
        if rotation_degrees % 360:
            transposed = transposed.rotate(-rotation_degrees, expand=True)
        # crop_box: (left, top, right, bottom)
        left, top, right, bottom = crop_box
        
        # Clamp to bounds
        left = max(0, min(left, transposed.width - 1))
        top = max(0, min(top, transposed.height - 1))
        right = max(left + 1, min(right, transposed.width))
        bottom = max(top + 1, min(bottom, transposed.height))

        cropped = transposed.crop((left, top, right, bottom))
        
        # Save keeping format
        img_format = img.format or "JPEG"
        save_kwargs = {}
        if transposed.info.get('icc_profile'):
            save_kwargs['icc_profile'] = transposed.info['icc_profile']
        if img_format.upper() in ("JPEG", "JPG"):
            save_kwargs["quality"] = 95
            save_kwargs["subsampling"] = 0
        elif img_format.upper() == "PNG":
            save_kwargs["compress_level"] = 6

    # Close the source before replacing it (required on Windows), and only
    # publish a completely encoded file. A failed save leaves the original intact.
    with tempfile.NamedTemporaryFile(prefix='.xnviewtab-crop-', suffix=dest.suffix,
                                     dir=dest.parent, delete=False) as temp:
        temp_dest = Path(temp.name)
    try:
        cropped.save(temp_dest, format=img_format, **save_kwargs)
        temp_dest.replace(dest)
    finally:
        temp_dest.unlink(missing_ok=True)

    return dest


def rotate_image_file(image_path: str | Path, degrees: int) -> Path:
    """Rotate an image in place atomically, after applying its EXIF orientation."""
    source = Path(image_path)
    if not source.is_file() or not is_image_file(source):
        raise OSError("Ce fichier image n'existe plus.")
    if degrees % 360 == 0:
        return source

    with Image.open(source) as opened:
        image_format = opened.format or 'PNG'
        image = ImageOps.exif_transpose(opened)
        image = image.rotate(-degrees, expand=True)
        save_kwargs = {}
        if image.info.get('icc_profile'):
            save_kwargs['icc_profile'] = image.info['icc_profile']
        if image.info.get('exif'):
            save_kwargs['exif'] = image.info['exif']
        if image_format.upper() in ('JPEG', 'JPG'):
            if image.mode not in ('RGB', 'L'):
                image = image.convert('RGB')
            save_kwargs.update(quality=95, subsampling=0)
        image.load()

    with tempfile.NamedTemporaryFile(prefix='.tabatab-rotate-', suffix=source.suffix,
                                     dir=source.parent, delete=False) as temporary:
        temp_path = Path(temporary.name)
    try:
        image.save(temp_path, format=image_format, **save_kwargs)
        temp_path.replace(source)
    finally:
        temp_path.unlink(missing_ok=True)
    return source
