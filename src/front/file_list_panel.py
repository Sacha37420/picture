"""
file_list_panel.py – left panel.

Displays the list of input files. Supports:
  - Drag-and-drop from the OS file manager onto the list.
  - "Add files" button (file dialog).
  - Drag reordering within the list.
  - "Remove selected" button.

Emits ``files_changed`` whenever the list is modified so the main
window can reload the MultiImage.
"""
from __future__ import annotations

import os
from typing import List

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_SUPPORTED_EXTS = {
    # Images
    ".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif",
    ".webp", ".gif", ".ico", ".ppm", ".tga",
    # Documents
    ".pdf",
    # Data / charts (text)
    ".csv", ".tsv", ".json", ".xlsx", ".xls",
    # Data / charts (binary / records)
    ".rec", ".sec", ".bin",
}


class _DnDListWidget(QListWidget):
    """QListWidget with internal drag-reorder + external file drop."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QListWidget.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        self.setToolTip("Glissez des fichiers ici ou utilisez le bouton Ajouter")

    # ---- external file drop (from OS) ----
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                ext = os.path.splitext(path)[1].lower()
                if os.path.isfile(path) and ext in _SUPPORTED_EXTS:
                    self._add_path(path)
            event.acceptProposedAction()
        else:
            # internal reorder
            super().dropEvent(event)
        # notify parent
        panel: FileListPanel = self.parent()
        if isinstance(panel, FileListPanel):
            panel.files_changed.emit(panel.file_paths())

    def _add_path(self, path: str):
        # avoid duplicates
        existing = [self.item(i).data(Qt.ItemDataRole.UserRole)
                    for i in range(self.count())]
        if path not in existing:
            item = QListWidgetItem(os.path.basename(path))
            item.setData(Qt.ItemDataRole.UserRole, path)
            item.setToolTip(path)
            self.addItem(item)


class FileListPanel(QWidget):
    """Left panel – ordered list of input files."""

    files_changed = pyqtSignal(list)   # emits list[str] of absolute paths

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QLabel("FICHIERS D'ENTRÉE")
        title.setObjectName("section_title")
        layout.addWidget(title)

        self._list = _DnDListWidget(self)
        layout.addWidget(self._list, stretch=1)

        # ---- buttons ----
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        self._btn_add = QPushButton("＋ Ajouter")
        self._btn_add.setToolTip("Ajouter des fichiers image ou PDF")
        self._btn_add.clicked.connect(self._on_add)
        btn_row.addWidget(self._btn_add)

        self._btn_remove = QPushButton("✕ Supprimer")
        self._btn_remove.setToolTip("Retirer le fichier sélectionné")
        self._btn_remove.clicked.connect(self._on_remove)
        btn_row.addWidget(self._btn_remove)

        layout.addLayout(btn_row)

        # ---- reorder buttons ----
        order_row = QHBoxLayout()
        order_row.setSpacing(6)

        self._btn_up = QPushButton("▲")
        self._btn_up.setToolTip("Monter")
        self._btn_up.setFixedWidth(40)
        self._btn_up.clicked.connect(self._on_move_up)
        order_row.addWidget(self._btn_up)

        self._btn_down = QPushButton("▼")
        self._btn_down.setToolTip("Descendre")
        self._btn_down.setFixedWidth(40)
        self._btn_down.clicked.connect(self._on_move_down)
        order_row.addWidget(self._btn_down)

        order_row.addStretch()
        layout.addLayout(order_row)

        # notify on internal reorder via model rows-moved
        self._list.model().rowsMoved.connect(self._on_rows_moved)

    # ------------------------------------------------------------------ #

    def _on_add(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Ajouter des fichiers",
            "",
            "Tous les fichiers supportés ("
            "*.png *.jpg *.jpeg *.bmp *.tiff *.tif "
            "*.webp *.gif *.ico *.ppm *.tga "
            "*.pdf "
            "*.csv *.tsv *.json *.xlsx *.xls"
            ");;"
            "Images (*.png *.jpg *.jpeg *.bmp *.tiff *.tif *.webp *.gif *.ico *.ppm *.tga);;"
            "PDF (*.pdf);;"
            "Données / Graphiques (*.csv *.tsv *.json *.xlsx *.xls *.rec *.sec *.bin)",
        )
        for p in paths:
            self._list._add_path(p)
        if paths:
            self.files_changed.emit(self.file_paths())

    def _on_remove(self):
        row = self._list.currentRow()
        if row >= 0:
            self._list.takeItem(row)
            self.files_changed.emit(self.file_paths())

    def _on_move_up(self):
        row = self._list.currentRow()
        if row > 0:
            item = self._list.takeItem(row)
            self._list.insertItem(row - 1, item)
            self._list.setCurrentRow(row - 1)
            self.files_changed.emit(self.file_paths())

    def _on_move_down(self):
        row = self._list.currentRow()
        if row < self._list.count() - 1:
            item = self._list.takeItem(row)
            self._list.insertItem(row + 1, item)
            self._list.setCurrentRow(row + 1)
            self.files_changed.emit(self.file_paths())

    def _on_rows_moved(self, *_):
        self.files_changed.emit(self.file_paths())

    # ------------------------------------------------------------------ #

    def file_paths(self) -> List[str]:
        return [
            self._list.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(self._list.count())
        ]
