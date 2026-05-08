"""
qt_compat.py – Qt binding compatibility shim.

Tries Qt bindings in this priority order:
  1. PyQt6   – native scoped enums, preferred
  2. PyQt5   – scoped-enum shims added to match PyQt6 API
  3. PySide6 – Signal aliased as pyqtSignal
  4. PySide2 – Signal aliased as pyqtSignal + scoped-enum shims

All callers use the single import::

    from .qt_compat import (
        Qt, pyqtSignal, QThread,
        QColor, QIcon, QImage, QPainter, QPen, QPixmap,
        QApplication, QCheckBox, QColorDialog, QComboBox, QDoubleSpinBox,
        QFileDialog, QFormLayout, QFrame, QGroupBox, QHBoxLayout, QLabel,
        QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
        QPushButton, QScrollArea, QSizePolicy, QSpinBox, QSplitter,
        QStatusBar, QVBoxLayout, QWidget,
    )

and use PyQt6-style scoped enums everywhere (e.g. ``Qt.AlignmentFlag.AlignCenter``).
"""
from __future__ import annotations

from types import SimpleNamespace as _NS


def _ns(**kw):
    """Return a SimpleNamespace populated from *kw*."""
    return _NS(**kw)


# ──────────────────────────────────────────────────────────────────────────────
# 1 · PyQt6
# ──────────────────────────────────────────────────────────────────────────────
try:
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    from PyQt6.QtGui import QColor, QIcon, QImage, QPainter, QPen, QPixmap
    from PyQt6.QtWidgets import (
        QApplication,
        QCheckBox,
        QColorDialog,
        QComboBox,
        QDoubleSpinBox,
        QFileDialog,
        QFormLayout,
        QFrame,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QListWidget,
        QListWidgetItem,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSpinBox,
        QSplitter,
        QStatusBar,
        QVBoxLayout,
        QWidget,
    )
    QT_BINDING = "PyQt6"

# ──────────────────────────────────────────────────────────────────────────────
# 2 · PyQt5  (add scoped-enum namespaces to match PyQt6 API)
# ──────────────────────────────────────────────────────────────────────────────
except ImportError:
    try:
        from PyQt5.QtCore import Qt as _Qt5, QThread, pyqtSignal
        from PyQt5.QtGui import QColor, QIcon, QImage, QPainter, QPen, QPixmap
        from PyQt5.QtWidgets import (
            QAbstractItemView as _QAIV5,
            QApplication,
            QCheckBox,
            QColorDialog,
            QComboBox,
            QDoubleSpinBox,
            QFileDialog,
            QFormLayout,
            QFrame,
            QGroupBox,
            QHBoxLayout,
            QLabel,
            QListWidget as _QLW5,
            QListWidgetItem,
            QMainWindow,
            QMessageBox as _QMB5,
            QPushButton,
            QScrollArea,
            QSizePolicy as _QSP5,
            QSpinBox,
            QSplitter,
            QStatusBar,
            QVBoxLayout,
            QWidget,
        )

        # ---- Qt namespace shim ----
        class Qt:  # type: ignore[no-redef]
            """PyQt5 Qt namespace with PyQt6-style scoped enum attributes."""

            AlignmentFlag = _ns(
                AlignLeft=_Qt5.AlignLeft,
                AlignRight=_Qt5.AlignRight,
                AlignCenter=_Qt5.AlignCenter,
                AlignHCenter=_Qt5.AlignHCenter,
                AlignVCenter=_Qt5.AlignVCenter,
                AlignTop=_Qt5.AlignTop,
                AlignBottom=_Qt5.AlignBottom,
                AlignJustify=_Qt5.AlignJustify,
            )
            DropAction = _ns(
                MoveAction=_Qt5.MoveAction,
                CopyAction=_Qt5.CopyAction,
                LinkAction=_Qt5.LinkAction,
                IgnoreAction=_Qt5.IgnoreAction,
            )
            ItemDataRole = _ns(
                DisplayRole=_Qt5.DisplayRole,
                DecorationRole=_Qt5.DecorationRole,
                EditRole=_Qt5.EditRole,
                ToolTipRole=_Qt5.ToolTipRole,
                UserRole=_Qt5.UserRole,
            )
            TransformationMode = _ns(
                FastTransformation=_Qt5.FastTransformation,
                SmoothTransformation=_Qt5.SmoothTransformation,
            )
            ScrollBarPolicy = _ns(
                ScrollBarAsNeeded=_Qt5.ScrollBarAsNeeded,
                ScrollBarAlwaysOff=_Qt5.ScrollBarAlwaysOff,
                ScrollBarAlwaysOn=_Qt5.ScrollBarAlwaysOn,
            )
            Orientation = _ns(
                Horizontal=_Qt5.Horizontal,
                Vertical=_Qt5.Vertical,
            )
            TextElideMode = _ns(
                ElideLeft=_Qt5.ElideLeft,
                ElideRight=_Qt5.ElideRight,
                ElideMiddle=_Qt5.ElideMiddle,
                ElideNone=_Qt5.ElideNone,
            )
            WindowModality = _ns(
                NonModal=_Qt5.NonModal,
                WindowModal=_Qt5.WindowModal,
                ApplicationModal=_Qt5.ApplicationModal,
            )

        # ---- QSizePolicy shim ----
        class QSizePolicy(_QSP5):  # type: ignore[no-redef]
            Policy = _ns(
                Fixed=_QSP5.Fixed,
                Minimum=_QSP5.Minimum,
                Maximum=_QSP5.Maximum,
                Preferred=_QSP5.Preferred,
                MinimumExpanding=_QSP5.MinimumExpanding,
                Expanding=_QSP5.Expanding,
                Ignored=_QSP5.Ignored,
            )

        # ---- QListWidget shim ----
        class QListWidget(_QLW5):  # type: ignore[no-redef]
            DragDropMode = _ns(
                NoDragDrop=_QAIV5.NoDragDrop,
                DragOnly=_QAIV5.DragOnly,
                DropOnly=_QAIV5.DropOnly,
                DragDrop=_QAIV5.DragDrop,
                InternalMove=_QAIV5.InternalMove,
            )
            SelectionMode = _ns(
                NoSelection=_QAIV5.NoSelection,
                SingleSelection=_QAIV5.SingleSelection,
                MultiSelection=_QAIV5.MultiSelection,
                ExtendedSelection=_QAIV5.ExtendedSelection,
                ContiguousSelection=_QAIV5.ContiguousSelection,
            )

        # ---- QMessageBox shim ----
        class QMessageBox(_QMB5):  # type: ignore[no-redef]
            Icon = _ns(
                NoIcon=_QMB5.NoIcon,
                Question=_QMB5.Question,
                Information=_QMB5.Information,
                Warning=_QMB5.Warning,
                Critical=_QMB5.Critical,
            )
            ButtonRole = _ns(
                InvalidRole=_QMB5.InvalidRole,
                AcceptRole=_QMB5.AcceptRole,
                RejectRole=_QMB5.RejectRole,
                DestructiveRole=_QMB5.DestructiveRole,
                ActionRole=_QMB5.ActionRole,
                HelpRole=_QMB5.HelpRole,
                YesRole=_QMB5.YesRole,
                NoRole=_QMB5.NoRole,
                ApplyRole=_QMB5.ApplyRole,
                ResetRole=_QMB5.ResetRole,
            )

        QT_BINDING = "PyQt5"

    # ──────────────────────────────────────────────────────────────────────────
    # 3 · PySide6  (Signal → pyqtSignal alias)
    # ──────────────────────────────────────────────────────────────────────────
    except ImportError:
        try:
            from PySide6.QtCore import Qt, QThread
            from PySide6.QtCore import Signal as pyqtSignal  # type: ignore[no-redef]
            from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPen, QPixmap
            from PySide6.QtWidgets import (
                QApplication,
                QCheckBox,
                QColorDialog,
                QComboBox,
                QDoubleSpinBox,
                QFileDialog,
                QFormLayout,
                QFrame,
                QGroupBox,
                QHBoxLayout,
                QLabel,
                QListWidget,
                QListWidgetItem,
                QMainWindow,
                QMessageBox,
                QPushButton,
                QScrollArea,
                QSizePolicy,
                QSpinBox,
                QSplitter,
                QStatusBar,
                QVBoxLayout,
                QWidget,
            )
            QT_BINDING = "PySide6"

        # ──────────────────────────────────────────────────────────────────────
        # 4 · PySide2  (Signal → pyqtSignal alias + scoped-enum shims)
        # ──────────────────────────────────────────────────────────────────────
        except ImportError:
            try:
                from PySide2.QtCore import Qt as _Qt2, QThread
                from PySide2.QtCore import Signal as pyqtSignal  # type: ignore[no-redef]
                from PySide2.QtGui import QColor, QIcon, QImage, QPainter, QPen, QPixmap
                from PySide2.QtWidgets import (
                    QAbstractItemView as _QAIV2,
                    QApplication,
                    QCheckBox,
                    QColorDialog,
                    QComboBox,
                    QDoubleSpinBox,
                    QFileDialog,
                    QFormLayout,
                    QFrame,
                    QGroupBox,
                    QHBoxLayout,
                    QLabel,
                    QListWidget as _QLW2,
                    QListWidgetItem,
                    QMainWindow,
                    QMessageBox as _QMB2,
                    QPushButton,
                    QScrollArea,
                    QSizePolicy as _QSP2,
                    QSpinBox,
                    QSplitter,
                    QStatusBar,
                    QVBoxLayout,
                    QWidget,
                )

                # ---- Qt namespace shim ----
                class Qt:  # type: ignore[no-redef]
                    AlignmentFlag = _ns(
                        AlignLeft=_Qt2.AlignLeft,
                        AlignRight=_Qt2.AlignRight,
                        AlignCenter=_Qt2.AlignCenter,
                        AlignHCenter=_Qt2.AlignHCenter,
                        AlignVCenter=_Qt2.AlignVCenter,
                        AlignTop=_Qt2.AlignTop,
                        AlignBottom=_Qt2.AlignBottom,
                        AlignJustify=_Qt2.AlignJustify,
                    )
                    DropAction = _ns(
                        MoveAction=_Qt2.MoveAction,
                        CopyAction=_Qt2.CopyAction,
                        LinkAction=_Qt2.LinkAction,
                        IgnoreAction=_Qt2.IgnoreAction,
                    )
                    ItemDataRole = _ns(
                        DisplayRole=_Qt2.DisplayRole,
                        DecorationRole=_Qt2.DecorationRole,
                        EditRole=_Qt2.EditRole,
                        ToolTipRole=_Qt2.ToolTipRole,
                        UserRole=_Qt2.UserRole,
                    )
                    TransformationMode = _ns(
                        FastTransformation=_Qt2.FastTransformation,
                        SmoothTransformation=_Qt2.SmoothTransformation,
                    )
                    ScrollBarPolicy = _ns(
                        ScrollBarAsNeeded=_Qt2.ScrollBarAsNeeded,
                        ScrollBarAlwaysOff=_Qt2.ScrollBarAlwaysOff,
                        ScrollBarAlwaysOn=_Qt2.ScrollBarAlwaysOn,
                    )
                    Orientation = _ns(
                        Horizontal=_Qt2.Horizontal,
                        Vertical=_Qt2.Vertical,
                    )
                    TextElideMode = _ns(
                        ElideLeft=_Qt2.ElideLeft,
                        ElideRight=_Qt2.ElideRight,
                        ElideMiddle=_Qt2.ElideMiddle,
                        ElideNone=_Qt2.ElideNone,
                    )
                    WindowModality = _ns(
                        NonModal=_Qt2.NonModal,
                        WindowModal=_Qt2.WindowModal,
                        ApplicationModal=_Qt2.ApplicationModal,
                    )

                # ---- QSizePolicy shim ----
                class QSizePolicy(_QSP2):  # type: ignore[no-redef]
                    Policy = _ns(
                        Fixed=_QSP2.Fixed,
                        Minimum=_QSP2.Minimum,
                        Maximum=_QSP2.Maximum,
                        Preferred=_QSP2.Preferred,
                        MinimumExpanding=_QSP2.MinimumExpanding,
                        Expanding=_QSP2.Expanding,
                        Ignored=_QSP2.Ignored,
                    )

                # ---- QListWidget shim ----
                class QListWidget(_QLW2):  # type: ignore[no-redef]
                    DragDropMode = _ns(
                        NoDragDrop=_QAIV2.NoDragDrop,
                        DragOnly=_QAIV2.DragOnly,
                        DropOnly=_QAIV2.DropOnly,
                        DragDrop=_QAIV2.DragDrop,
                        InternalMove=_QAIV2.InternalMove,
                    )
                    SelectionMode = _ns(
                        NoSelection=_QAIV2.NoSelection,
                        SingleSelection=_QAIV2.SingleSelection,
                        MultiSelection=_QAIV2.MultiSelection,
                        ExtendedSelection=_QAIV2.ExtendedSelection,
                        ContiguousSelection=_QAIV2.ContiguousSelection,
                    )

                # ---- QMessageBox shim ----
                class QMessageBox(_QMB2):  # type: ignore[no-redef]
                    Icon = _ns(
                        NoIcon=_QMB2.NoIcon,
                        Question=_QMB2.Question,
                        Information=_QMB2.Information,
                        Warning=_QMB2.Warning,
                        Critical=_QMB2.Critical,
                    )
                    ButtonRole = _ns(
                        InvalidRole=_QMB2.InvalidRole,
                        AcceptRole=_QMB2.AcceptRole,
                        RejectRole=_QMB2.RejectRole,
                        DestructiveRole=_QMB2.DestructiveRole,
                        ActionRole=_QMB2.ActionRole,
                        HelpRole=_QMB2.HelpRole,
                        YesRole=_QMB2.YesRole,
                        NoRole=_QMB2.NoRole,
                        ApplyRole=_QMB2.ApplyRole,
                        ResetRole=_QMB2.ResetRole,
                    )

                QT_BINDING = "PySide2"

            # ──────────────────────────────────────────────────────────────────
            # 5 · PyQt4  (no QtWidgets – everything lives in QtGui)
            # ──────────────────────────────────────────────────────────────────
            except ImportError:
                try:
                    from PyQt4.QtCore import Qt as _Qt4, QThread, pyqtSignal  # type: ignore[no-redef]
                    # In PyQt4 all GUI classes are in QtGui (no QtWidgets module)
                    from PyQt4.QtGui import (  # type: ignore[no-redef]
                        QAbstractItemView as _QAIV4,
                        QApplication,
                        QCheckBox,
                        QColor,
                        QColorDialog,
                        QComboBox,
                        QDoubleSpinBox,
                        QFileDialog,
                        QFormLayout,
                        QFrame,
                        QGroupBox,
                        QHBoxLayout,
                        QIcon,
                        QImage,
                        QLabel,
                        QListWidget as _QLW4,
                        QListWidgetItem,
                        QMainWindow,
                        QMessageBox as _QMB4,
                        QPainter,
                        QPen,
                        QPixmap,
                        QPushButton,
                        QScrollArea,
                        QSizePolicy as _QSP4,
                        QSpinBox,
                        QSplitter,
                        QStatusBar,
                        QVBoxLayout,
                        QWidget,
                    )

                    # ---- Qt namespace shim ----
                    class Qt:  # type: ignore[no-redef]
                        AlignmentFlag = _ns(
                            AlignLeft=_Qt4.AlignLeft,
                            AlignRight=_Qt4.AlignRight,
                            AlignCenter=_Qt4.AlignCenter,
                            AlignHCenter=_Qt4.AlignHCenter,
                            AlignVCenter=_Qt4.AlignVCenter,
                            AlignTop=_Qt4.AlignTop,
                            AlignBottom=_Qt4.AlignBottom,
                            AlignJustify=_Qt4.AlignJustify,
                        )
                        DropAction = _ns(
                            MoveAction=_Qt4.MoveAction,
                            CopyAction=_Qt4.CopyAction,
                            LinkAction=_Qt4.LinkAction,
                            IgnoreAction=_Qt4.IgnoreAction,
                        )
                        ItemDataRole = _ns(
                            DisplayRole=_Qt4.DisplayRole,
                            DecorationRole=_Qt4.DecorationRole,
                            EditRole=_Qt4.EditRole,
                            ToolTipRole=_Qt4.ToolTipRole,
                            UserRole=_Qt4.UserRole,
                        )
                        TransformationMode = _ns(
                            FastTransformation=_Qt4.FastTransformation,
                            SmoothTransformation=_Qt4.SmoothTransformation,
                        )
                        ScrollBarPolicy = _ns(
                            ScrollBarAsNeeded=_Qt4.ScrollBarAsNeeded,
                            ScrollBarAlwaysOff=_Qt4.ScrollBarAlwaysOff,
                            ScrollBarAlwaysOn=_Qt4.ScrollBarAlwaysOn,
                        )
                        Orientation = _ns(
                            Horizontal=_Qt4.Horizontal,
                            Vertical=_Qt4.Vertical,
                        )
                        TextElideMode = _ns(
                            ElideLeft=_Qt4.ElideLeft,
                            ElideRight=_Qt4.ElideRight,
                            ElideMiddle=_Qt4.ElideMiddle,
                            ElideNone=_Qt4.ElideNone,
                        )
                        WindowModality = _ns(
                            NonModal=_Qt4.NonModal,
                            WindowModal=_Qt4.WindowModal,
                            ApplicationModal=_Qt4.ApplicationModal,
                        )

                    # ---- QSizePolicy shim ----
                    class QSizePolicy(_QSP4):  # type: ignore[no-redef]
                        Policy = _ns(
                            Fixed=_QSP4.Fixed,
                            Minimum=_QSP4.Minimum,
                            Maximum=_QSP4.Maximum,
                            Preferred=_QSP4.Preferred,
                            MinimumExpanding=_QSP4.MinimumExpanding,
                            Expanding=_QSP4.Expanding,
                            Ignored=_QSP4.Ignored,
                        )

                    # ---- QListWidget shim ----
                    class QListWidget(_QLW4):  # type: ignore[no-redef]
                        DragDropMode = _ns(
                            NoDragDrop=_QAIV4.NoDragDrop,
                            DragOnly=_QAIV4.DragOnly,
                            DropOnly=_QAIV4.DropOnly,
                            DragDrop=_QAIV4.DragDrop,
                            InternalMove=_QAIV4.InternalMove,
                        )
                        SelectionMode = _ns(
                            NoSelection=_QAIV4.NoSelection,
                            SingleSelection=_QAIV4.SingleSelection,
                            MultiSelection=_QAIV4.MultiSelection,
                            ExtendedSelection=_QAIV4.ExtendedSelection,
                            ContiguousSelection=_QAIV4.ContiguousSelection,
                        )

                    # ---- QMessageBox shim ----
                    class QMessageBox(_QMB4):  # type: ignore[no-redef]
                        Icon = _ns(
                            NoIcon=_QMB4.NoIcon,
                            Question=_QMB4.Question,
                            Information=_QMB4.Information,
                            Warning=_QMB4.Warning,
                            Critical=_QMB4.Critical,
                        )
                        ButtonRole = _ns(
                            InvalidRole=_QMB4.InvalidRole,
                            AcceptRole=_QMB4.AcceptRole,
                            RejectRole=_QMB4.RejectRole,
                            DestructiveRole=_QMB4.DestructiveRole,
                            ActionRole=_QMB4.ActionRole,
                            HelpRole=_QMB4.HelpRole,
                            YesRole=_QMB4.YesRole,
                            NoRole=_QMB4.NoRole,
                            ApplyRole=_QMB4.ApplyRole,
                            ResetRole=_QMB4.ResetRole,
                        )

                    QT_BINDING = "PyQt4"

                except ImportError as _exc:
                    raise ImportError(
                        "No supported Qt binding found. "
                        "Install one of: PyQt6, PyQt5, PySide6, PySide2, PyQt4.\n"
                        "  pip install PyQt6\n"
                        "  pip install PyQt5\n"
                        "  pip install PySide6\n"
                        "  pip install PySide2\n"
                        "  pip install PyQt4  # legacy, Python 3.x wheel required"
                    ) from _exc


__all__ = [
    "QT_BINDING",
    "Qt",
    "QThread",
    "pyqtSignal",
    "QColor",
    "QIcon",
    "QImage",
    "QPainter",
    "QPen",
    "QPixmap",
    "QApplication",
    "QCheckBox",
    "QColorDialog",
    "QComboBox",
    "QDoubleSpinBox",
    "QFileDialog",
    "QFormLayout",
    "QFrame",
    "QGroupBox",
    "QHBoxLayout",
    "QLabel",
    "QListWidget",
    "QListWidgetItem",
    "QMainWindow",
    "QMessageBox",
    "QPushButton",
    "QScrollArea",
    "QSizePolicy",
    "QSpinBox",
    "QSplitter",
    "QStatusBar",
    "QVBoxLayout",
    "QWidget",
]
