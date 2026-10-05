"""Publish a verified Windows bundle, excluding personal settings."""
import argparse
import hashlib
import shutil
import subprocess
import zipfile
from pathlib import Path
from src.version import APP_VERSION, APP_NAME

ROOT = Path(__file__).resolve().parent


def run(*args, capture=False):
    return subprocess.run(args, cwd=ROOT, check=True, text=True,
                          capture_output=capture)


def package_release(bundle, output):
    bundle, output = Path(bundle), Path(output)
    if not (bundle / 'TABaTAB Cash.exe').is_file() or not (bundle / '_internal').is_dir():
        raise FileNotFoundError('Version portable complète introuvable. Compiler avant de publier.')
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f'{bundle.name}_Windows_x64.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zipped:
        for source in sorted(bundle.rglob('*')):
            relative = source.relative_to(bundle)
            if source.is_file() and relative.parts[0] != 'data':
                zipped.write(source, Path(bundle.name) / relative)
    with archive.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    checksum = archive.with_suffix('.zip.sha256')
    checksum.write_text(f'{digest}  {archive.name}\n', encoding='utf-8')
    return archive, checksum


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--notes', type=Path, required=True)
    args = parser.parse_args()
    notes = args.notes.resolve()
    if not notes.is_file():
        raise FileNotFoundError(notes)
    gh = shutil.which('gh')
    if not gh:
        installed = Path(r'C:\Program Files\GitHub CLI\gh.exe')
        gh = str(installed) if installed.is_file() else None
    if not gh:
        raise RuntimeError('Installer GitHub CLI et se connecter avec gh auth login.')
    run(gh, 'auth', 'status')
    if run('git', 'status', '--porcelain', capture=True).stdout.strip():
        raise RuntimeError('Commiter les modifications avant de publier.')
    commit = run('git', 'rev-parse', 'HEAD', capture=True).stdout.strip()
    tag = f'v{APP_VERSION}'
    existing = subprocess.run([gh, 'release', 'view', tag], cwd=ROOT, capture_output=True)
    if existing.returncode == 0:
        raise RuntimeError(f'La release {tag} existe déjà. Incrémenter la version.')
    archive, checksum = package_release(ROOT / f'TABaTAB_Cash_Portable_v{APP_VERSION}', ROOT / 'release')
    run('git', 'push', 'origin', 'HEAD')
    run(gh, 'release', 'create', tag, str(archive), str(checksum), '--target', commit,
        '--title', f'{APP_NAME} {APP_VERSION}', '--notes-file', str(notes))
    run(gh, 'release', 'view', tag, '--json', 'url,tagName,assets')


if __name__ == '__main__':
    main()
