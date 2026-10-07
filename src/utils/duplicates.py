"""Exact, non-recursive duplicate detection and conservative recycling."""
import hashlib
import threading
from pathlib import Path
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, QFile


def digest_file(path, cancelled=lambda: False):
    before = path.stat()
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1024 * 1024):
            if cancelled(): raise InterruptedError('Recherche annulée')
            digest.update(block)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise OSError(f'Fichier modifié pendant la lecture : {path.name}')
    return digest.hexdigest()


def find_duplicates(folder, cancelled=lambda: False):
    sizes, groups, errors = {}, {}, []
    for path in sorted(Path(folder).iterdir(), key=lambda p: (p.name.casefold(), p.name)):
        if cancelled(): raise InterruptedError('Recherche annulée')
        try:
            if path.is_file() and not path.is_symlink():
                sizes.setdefault(path.stat().st_size, []).append(path)
        except OSError as error: errors.append(f'{path.name} : {error}')
    for paths in sizes.values():
        if len(paths) < 2: continue
        for path in paths:
            try:
                groups.setdefault(digest_file(path, cancelled), []).append(path)
            except OSError as error:
                if isinstance(error, InterruptedError): raise
                errors.append(f'{path.name} : {error}')
    return [(digest, paths) for digest, paths in groups.items() if len(paths) > 1], errors


def recycle_duplicates(groups):
    removed, errors = [], []
    for digest, paths in groups:
        keeper = paths[0]
        for duplicate in paths[1:]:
            try:
                if keeper.is_symlink() or duplicate.is_symlink(): raise OSError('Lien ignoré')
                if digest_file(keeper) != digest or digest_file(duplicate) != digest:
                    raise OSError('Contenu modifié depuis la recherche ; fichier conservé')
                if not QFile(str(duplicate)).moveToTrash():
                    raise OSError('Corbeille indisponible ; fichier conservé')
                removed.append(str(duplicate))
            except OSError as error: errors.append(f'{duplicate.name} : {error}')
    return removed, errors


class ScanSignals(QObject):
    finished = pyqtSignal(object, object)


class DuplicateScan(QRunnable):
    def __init__(self, folder):
        super().__init__()
        self.folder = folder
        self.signals = ScanSignals()
        self.cancelled = threading.Event()

    def cancel(self): self.cancelled.set()

    def run(self):
        try: groups, errors = find_duplicates(self.folder, self.cancelled.is_set)
        except InterruptedError: groups, errors = None, []
        except OSError as error: groups, errors = [], [str(error)]
        self.signals.finished.emit(groups, errors)
