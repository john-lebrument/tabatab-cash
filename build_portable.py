"""Build a fresh minimal portable bundle, preserving existing releases."""
import shutil
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from src.version import APP_VERSION
import hashlib
import stat
import uuid
import argparse

LATEST_DIRECTORY = Path(os.environ.get('TABATAB_LATEST_DIRECTORY', str(Path.home() / 'OneDrive - unicaen.fr' / 'Setup 1D' / '__Last version')))


def _retry_readonly_removal(function, path, _error):
    """OneDrive may mark synchronized release files and folders read-only."""
    os.chmod(path, stat.S_IWRITE)
    function(path)


def publish_latest(release, latest_directory=LATEST_DIRECTORY):
    """Verify the new bundle before removing older releases of this application."""
    release = Path(release).resolve()
    latest = Path(latest_directory).resolve()
    latest.mkdir(parents=True, exist_ok=True)
    destination = latest / release.name
    if destination.exists():
        raise FileExistsError(f'Version déjà publiée : {destination}')
    stage = latest / ('.tabatab-' + uuid.uuid4().hex)
    shutil.copytree(release, stage)
    for source in release.rglob('*'):
        if source.is_file():
            copied = stage / source.relative_to(release)
            with source.open('rb') as original, copied.open('rb') as duplicate:
                if hashlib.file_digest(original, 'sha256').digest() != hashlib.file_digest(duplicate, 'sha256').digest():
                    raise OSError(f'Copie non vérifiée : {copied}')
    stage.rename(destination)
    for previous in latest.iterdir():
        if previous == destination or not previous.name.startswith(('TABaTAB_Cash_Portable_', 'XNViewTab_Portable_')):
            continue
        if previous.is_symlink() or previous.is_junction() or previous.resolve().parent != latest:
            raise OSError(f'Chemin de suppression non sûr : {previous}')
        if previous.is_dir():
            shutil.rmtree(previous, onexc=_retry_readonly_removal)
    return destination

def build(publish=True, include_settings=True):
    root = Path(__file__).resolve().parent
    target = root / f'TABaTAB_Cash_Portable_v{APP_VERSION}'
    if target.exists():
        raise FileExistsError('Incrémentez APP_VERSION avant de compiler une nouvelle version.')
    work = Path(tempfile.mkdtemp(prefix="xnviewtab-build-"))
    # Do not resolve Windows libraries from unrelated tools on the caller's PATH.
    env = os.environ.copy()
    env['PATH'] = os.pathsep.join([
        str(Path(sys.executable).parent),
        str(Path(sys.base_prefix)),
        str(Path(env.get('SystemRoot', 'C:/Windows')) / 'System32'),
        env.get('SystemRoot', 'C:/Windows'),
    ])
    subprocess.run([
        sys.executable, "-m", "PyInstaller", "--noconfirm",
        f"--workpath={work / 'work'}", f"--distpath={work / 'dist'}",
        str(root / "XNViewTab.spec"),
    ], cwd=root, env=env, check=True)
    shutil.copytree(work / "dist" / "TABaTAB Cash", target)
    candidates = list(root.glob('XNViewTab_Portable*/data/settings.json'))
    candidates.extend(root.glob('TABaTAB_Cash_Portable*/data/settings.json'))
    candidates.append(root / 'data' / 'settings.json')
    candidates = [path for path in candidates if path.exists()]
    settings = max(candidates, key=lambda path: path.stat().st_mtime) if candidates else root / 'data' / 'settings.json'
    if include_settings and settings.exists():
        (target / "data").mkdir()
        shutil.copy2(settings, target / "data" / "settings.json")
    print(f"Portable build: {target}", flush=True)
    for name in ('Lancer_TABaTAB_Cash.bat', 'Lancer_XNViewTab.bat'):
        (root / name).write_text('@echo off\ncd /d "%~dp0"\nstart "" "' + target.name + '\\TABaTAB Cash.exe" %*\n', encoding='utf-8')
    if publish:
        published = publish_latest(target)
        print(f'Dernière version : {published}', flush=True)
    return target

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-publish', action='store_true', help='Ne pas copier dans le dossier OneDrive local.')
    parser.add_argument('--clean-settings', action='store_true', help='Ne pas inclure les préférences personnelles.')
    args = parser.parse_args()
    build(publish=not args.no_publish, include_settings=not args.clean_settings)
