"""Folder actions shared by the grid and the directory tree."""
import re
from pathlib import Path
from PyQt6.QtCore import QFile
from PyQt6.QtWidgets import QInputDialog, QMessageBox


def create_folder(parent, directory):
    name, accepted = QInputDialog.getText(parent, 'Nouveau dossier', 'Nom du nouveau dossier :', text='Nouveau dossier')
    if not accepted:
        return None
    name = name.strip()
    try:
        if (not name or name in ('.', '..') or name.endswith('.')
                or re.search(r'[<>:"/\\|?*\x00-\x1f]', name)
                or re.fullmatch(r'(?i)(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?', name)):
            raise ValueError('Ce nom de dossier est invalide.')
        target = Path(directory).resolve() / name
        target.mkdir()  # Never reuse or replace an existing item.
        return str(target)
    except (OSError, ValueError) as error:
        QMessageBox.warning(parent, 'Création impossible', str(error))
        return None


def delete_folders(parent, paths):
    folders = [Path(p).absolute() for p in paths]
    folders = [p for p in folders if not any(other != p and other in p.parents for other in folders)]
    if not folders:
        return []
    names = '\n'.join(str(p) for p in folders[:8])
    if len(folders) > 8:
        names += f'\n… et {len(folders) - 8} autre(s) dossier(s)'
    reply = QMessageBox.question(parent, 'Confirmer la suppression des dossiers',
        f'Mettre ces {len(folders)} dossier(s) et tout leur contenu dans la corbeille ?\n\n{names}',
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
    if reply != QMessageBox.StandardButton.Yes:
        return []
    deleted = []
    for folder in folders:
        try:
            if not folder.is_dir() or folder.resolve() == Path(folder.resolve().anchor):
                raise OSError('Ce dossier ne peut pas être supprimé.')
            file = QFile(str(folder))
            if not file.moveToTrash():
                raise OSError(file.errorString() or 'La corbeille est indisponible.')
            deleted.append(str(folder))
        except OSError as error:
            QMessageBox.warning(parent, 'Suppression impossible', f'{folder}\n{error}')
    return deleted
