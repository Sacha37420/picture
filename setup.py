"""
setup.py – cx_Freeze build configuration.

Targets
-------
  python setup.py build_exe   → dist/exe.<platform>/   (standalone folder)
  python setup.py bdist_msi   → dist/*.msi              (Windows installer)
  python setup.py bdist_mac   → dist/*.dmg               (macOS, requires dmgbuild)

The same file is also called by build.bat / build.sh.
"""
import sys
import os
from pathlib import Path
from cx_Freeze import setup, Executable

# ------------------------------------------------------------------ #
# Metadata                                                             #
# ------------------------------------------------------------------ #
NAME        = "Picture"
VERSION     = "1.0.0"
DESCRIPTION = "Éditeur d'images et de PDF multi-format"
AUTHOR      = ""
ICON_WIN    = "assets/icon.ico"   # optional – ignored if file is absent
ICON_MAC    = "assets/icon.icns"  # optional
UPGRADE_CODE = "{A3F2C1D0-7B4E-4F8A-9C2D-1E6B5A3F2C1D}"  # keep stable across versions

# ------------------------------------------------------------------ #
# Packages / modules that cx_Freeze may miss through static analysis   #
# ------------------------------------------------------------------ #
INCLUDES = [
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PIL",
    "PIL.Image",
    "numpy",
    "fitz",                    # PyMuPDF
    "src.back",
    "src.front",
]

PACKAGES = [
    "PyQt6",
    "PIL",
    "numpy",
    "fitz",
    "src",
]

EXCLUDES = [
    "tkinter",
    "unittest",
    "email",
    "html",
    "http",
    "urllib",
    "xmlrpc",
    "pydoc",
    "doctest",
    "difflib",
    "distutils",
]

# Extra non-Python files to bundle
INCLUDE_FILES = []

# Include src/ package so relative imports work inside the frozen exe
INCLUDE_FILES.append(("src", "src"))

# Include icon if it exists
if os.path.isfile(ICON_WIN):
    INCLUDE_FILES.append((ICON_WIN, os.path.basename(ICON_WIN)))

# ------------------------------------------------------------------ #
# build_exe options                                                    #
# ------------------------------------------------------------------ #
build_exe_options = {
    "packages":      PACKAGES,
    "includes":      INCLUDES,
    "excludes":      EXCLUDES,
    "include_files": INCLUDE_FILES,
    "optimize":      1,          # .pyc optimisation level
    "build_exe":     "dist/exe", # output folder
    "zip_include_packages": "*",
    "zip_exclude_packages": "",
}

# ------------------------------------------------------------------ #
# bdist_msi options (Windows only)                                    #
# ------------------------------------------------------------------ #
bdist_msi_options = {
    "upgrade_code":       UPGRADE_CODE,
    "add_to_path":        False,
    "initial_target_dir": rf"[ProgramFilesFolder]\{NAME}",
    "summary_data": {
        "author":   AUTHOR,
        "comments": DESCRIPTION,
    },
    # Create a shortcut on the Desktop and in the Start Menu
    "data": {
        "Shortcut": [
            (
                "DesktopShortcut",          # Shortcut
                "DesktopFolder",            # Directory_
                NAME,                       # Name
                "TARGETDIR",                # Component_
                f"[TARGETDIR]{NAME}.exe",   # Target
                None, None, None, None, None, None,
                f"[TARGETDIR]{NAME}.exe",   # IconIndex
            ),
            (
                "StartMenuShortcut",
                "StartMenuFolder",
                NAME,
                "TARGETDIR",
                f"[TARGETDIR]{NAME}.exe",
                None, None, None, None, None, None,
                f"[TARGETDIR]{NAME}.exe",
            ),
        ]
    },
}

# ------------------------------------------------------------------ #
# bdist_dmg / bdist_mac options (macOS)                               #
# ------------------------------------------------------------------ #
bdist_dmg_options = {
    "applications_shortcut": True,
    "volume_label": NAME,
}

bdist_mac_options = {
    "bundle_name": NAME,
    "iconfile":    ICON_MAC if os.path.isfile(ICON_MAC) else None,
}

# ------------------------------------------------------------------ #
# Executable definition                                                #
# ------------------------------------------------------------------ #
_icon = ICON_WIN if sys.platform == "win32" and os.path.isfile(ICON_WIN) else (
    ICON_MAC if sys.platform == "darwin" and os.path.isfile(ICON_MAC) else None
)

executables = [
    Executable(
        script      = "main.py",
        base        = "Win32GUI" if sys.platform == "win32" else None,
        target_name = f"{NAME}.exe" if sys.platform == "win32" else NAME,
        icon        = _icon,
        copyright   = f"© {AUTHOR}" if AUTHOR else None,
    )
]

# ------------------------------------------------------------------ #
# setup()                                                              #
# ------------------------------------------------------------------ #
setup(
    name        = NAME,
    version     = VERSION,
    description = DESCRIPTION,
    author      = AUTHOR,
    options = {
        "build_exe":  build_exe_options,
        "bdist_msi":  bdist_msi_options,
        "bdist_mac":  bdist_mac_options,
        "bdist_dmg":  bdist_dmg_options,
    },
    executables = executables,
)
