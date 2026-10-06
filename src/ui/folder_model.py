"""Natural folder order, with underscore prefixes before numeric names."""
import re
from PyQt6.QtCore import QModelIndex, QSortFilterProxyModel, Qt
from PyQt6.QtGui import QFileSystemModel


def folder_sort_key(name):
    group = 0 if name.startswith('_') else (1 if name[:1].isdigit() else 2)
    parts = tuple((0, int(part)) if part.isdigit() else (1, part.casefold())
                  for part in re.split(r'(\d+)', name))
    return group, parts, name.casefold()


class FolderModel(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSourceModel(QFileSystemModel(self))
        self.setDynamicSortFilter(True)
        self.sort(0, Qt.SortOrder.AscendingOrder)

    def lessThan(self, left, right):
        source = self.sourceModel()
        return folder_sort_key(source.fileName(left)) < folder_sort_key(source.fileName(right))

    def index(self, row_or_path, column=0, parent=QModelIndex()):
        if isinstance(row_or_path, str):
            return self.mapFromSource(self.sourceModel().index(row_or_path, column))
        return super().index(row_or_path, column, parent)

    def setRootPath(self, path):
        return self.mapFromSource(self.sourceModel().setRootPath(path))

    def setFilter(self, filters):
        self.sourceModel().setFilter(filters)

    def filePath(self, index):
        return self.sourceModel().filePath(self.mapToSource(index))

    def fileIcon(self, index):
        return self.sourceModel().fileIcon(self.mapToSource(index))
