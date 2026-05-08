"""
src/install.py – automatic dependency checker / installer.

Called by main.py BEFORE any third-party import so that missing packages
are installed on the fly via pip.  Falls back to a plain terminal prompt
if PyQt6 is not yet available to show the GUI dialog.

Usage (in main.py)
------------------
    from src.install import ensure_dependencies
    ensure_dependencies()        # must be called before all other imports
"""
from __future__ import annotations

import importlib
import importlib.util
import subprocess
import sys
from typing import List, Tuple

# ---- Qt binding candidates (tried in priority order) ----
_QT_CANDIDATES = [
    ("PyQt6",   "PyQt6>=6.6.0"),
    ("PyQt5",   "PyQt5>=5.15.0"),
    ("PySide6", "PySide6>=6.6.0"),
    ("PySide2", "PySide2>=5.15.0"),
    ("PyQt4",   "PyQt4"),          # legacy – no versioned PyPI release
]


def _any_qt_available() -> bool:
    """Return True if at least one supported Qt binding is importable."""
    return any(
        importlib.util.find_spec(name) is not None
        for name, _ in _QT_CANDIDATES
    )


def _qt_pip_spec() -> str:
    """Return the pip spec for the first Qt binding that seems available,
    or the preferred one (PyQt6) if none is installed."""
    for name, spec in _QT_CANDIDATES:
        if importlib.util.find_spec(name) is not None:
            return spec
    return _QT_CANDIDATES[0][1]  # default: PyQt6


# (import_name, pip_package_name, human_label)
_REQUIRED: List[Tuple[str, str, str]] = [
    ("PIL",        "Pillow>=10.3.0",    "Pillow"),
    ("numpy",      "numpy>=1.26.0",     "NumPy"),
    ("fitz",       "pymupdf>=1.24.0",   "PyMuPDF"),
    ("matplotlib", "matplotlib>=3.8.0", "Matplotlib"),
    ("pandas",     "pandas>=2.1.0",     "pandas"),
    ("openpyxl",   "openpyxl>=3.1.0",   "openpyxl"),
]


def _qt_missing() -> bool:
    """Return True if no Qt binding is importable."""
    return not _any_qt_available()


def _missing() -> List[Tuple[str, str, str]]:
    """Return entries from _REQUIRED whose import_name cannot be found,
    plus a Qt entry if no supported Qt binding is installed."""
    missing = []
    # Check non-Qt dependencies
    for import_name, pip_pkg, label in _REQUIRED:
        try:
            importlib.import_module(import_name)
        except ModuleNotFoundError:
            missing.append((import_name, pip_pkg, label))
    # Check Qt separately: add the preferred available candidate, or PyQt6 as default
    if _qt_missing():
        missing.append(("_qt", _qt_pip_spec(), "Qt (PyQt6/PyQt5/PySide6/PySide2)"))
    return missing


def _install(pip_specs: List[str]) -> Tuple[bool, str]:
    """Run pip to install *pip_specs*. Returns (success, output)."""
    cmd = [sys.executable, "-m", "pip", "install", "--upgrade"] + pip_specs
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return result.returncode == 0, result.stdout


def _prompt_terminal(missing: List[Tuple[str, str, str]]) -> bool:
    """
    Ask the user in the terminal whether to install missing packages.
    Returns True if installation should proceed.
    """
    labels = ", ".join(label for _, _, label in missing)
    print(
        f"\n[Picture] Dépendances manquantes : {labels}\n"
        "Voulez-vous les installer maintenant ? [O/n] ",
        end="",
        flush=True,
    )
    answer = input().strip().lower()
    return answer in ("", "o", "oui", "y", "yes")


def _import_qt_widgets():
    """Import QApplication and QMessageBox from the first available Qt binding."""
    for name, _ in _QT_CANDIDATES:
        try:
            if name == "PyQt6":
                from PyQt6.QtWidgets import QApplication, QMessageBox
                return QApplication, QMessageBox, "PyQt6"
            if name == "PyQt5":
                from PyQt5.QtWidgets import QApplication, QMessageBox
                return QApplication, QMessageBox, "PyQt5"
            if name == "PySide6":
                from PySide6.QtWidgets import QApplication, QMessageBox
                return QApplication, QMessageBox, "PySide6"
            if name == "PySide2":
                from PySide2.QtWidgets import QApplication, QMessageBox
                return QApplication, QMessageBox, "PySide2"
            if name == "PyQt4":
                # PyQt4 has no QtWidgets – everything is in QtGui
                from PyQt4.QtGui import QApplication, QMessageBox  # type: ignore[no-redef]
                return QApplication, QMessageBox, "PyQt4"
        except ImportError:
            continue
    raise ImportError("No Qt binding available")


def _qmessagebox_icon_question(QMessageBox, binding: str):
    """Return the 'Question' icon enum value for the given Qt binding."""
    if binding in ("PyQt6", "PySide6"):
        return QMessageBox.Icon.Question
    return QMessageBox.Question


def _qmessagebox_role(QMessageBox, binding: str, role: str):
    """Return a ButtonRole enum value for the given Qt binding."""
    if binding in ("PyQt6", "PySide6"):
        return getattr(QMessageBox.ButtonRole, role)
    return getattr(QMessageBox, role)


def _prompt_gui(missing: List[Tuple[str, str, str]]) -> bool:
    """
    Show a Qt message box asking whether to install.
    Returns True if the user clicks Install.
    Only called when a Qt binding is available but other packages are missing.
    """
    QApplication, QMessageBox, binding = _import_qt_widgets()
    app = QApplication.instance() or QApplication(sys.argv)
    labels = "\n".join(f"  • {label}  ({pip})" for _, pip, label in missing)
    box = QMessageBox()
    box.setWindowTitle("Dépendances manquantes – Picture")
    box.setText(
        "Les paquets suivants sont requis mais ne sont pas installés :\n\n"
        f"{labels}\n\n"
        "Voulez-vous les installer maintenant ?"
    )
    box.setIcon(_qmessagebox_icon_question(QMessageBox, binding))
    btn_yes = box.addButton("Installer", _qmessagebox_role(QMessageBox, binding, "AcceptRole"))
    box.addButton("Quitter", _qmessagebox_role(QMessageBox, binding, "RejectRole"))
    box.exec()
    return box.clickedButton() is btn_yes


def ensure_dependencies() -> None:
    """
    Check that all required packages are importable.
    If any are missing, prompt the user and install them via pip.
    Exits with code 1 if the user declines or installation fails.
    """
    # When running as a frozen/compiled executable (cx_Freeze, PyInstaller…)
    # all dependencies are already bundled – skip the check entirely.
    if getattr(sys, "frozen", False):
        return

    missing = _missing()
    if not missing:
        return

    # Decide how to prompt: GUI if any Qt binding is already available, else terminal
    proceed = _prompt_terminal(missing) if _qt_missing() else _prompt_gui(missing)

    if not proceed:
        print("[Picture] Installation annulée. Fermeture.")
        sys.exit(1)

    pip_specs = [pip for _, pip, _ in missing]
    labels    = [label for _, _, label in missing]
    print(f"\n[Picture] Installation de : {', '.join(labels)} …")
    ok, output = _install(pip_specs)

    if not ok:
        print("[Picture] Erreur lors de l'installation :\n")
        print(output)
        # Try once more with a GUI error if Qt is now available
        try:
            QApplication, QMessageBox, _binding = _import_qt_widgets()
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(
                None,
                "Erreur d'installation",
                f"L'installation a échoué :\n\n{output[-800:]}\n\n"
                "Relancez le programme après avoir installé manuellement :\n"
                f"  pip install {' '.join(pip_specs)}",
            )
        except Exception:
            pass
        sys.exit(1)

    # Verify that the packages are now importable
    still_missing = _missing()
    if still_missing:
        labels_fail = ", ".join(label for _, _, label in still_missing)
        print(
            f"[Picture] Installation terminée mais {labels_fail} reste(nt) "
            "introuvable(s). Vérifiez votre environnement Python."
        )
        sys.exit(1)

    print("[Picture] Dépendances installées avec succès.\n")
