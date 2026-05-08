#!/usr/bin/env bash
# ===================================================================
#  build.sh  –  Picture build script (Linux / macOS)
#
#  Usage
#  -----
#    ./build.sh              →  build all targets
#    ./build.sh exe          →  standalone folder only  (dist/exe/)
#    ./build.sh dmg          →  macOS .dmg bundle        (macOS only)
#    ./build.sh pyinstaller  →  single-file binary via PyInstaller
#    ./build.sh clean        →  remove build/ and dist/
# ===================================================================
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"
TARGET="${1:-all}"

echo
echo " ========================================="
echo "  Picture – Build Script"
echo "  Platform : $(uname -s)"
echo "  Target   : $TARGET"
echo " ========================================="
echo

# ── check python ──────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 not found. Install Python 3.10+ first."
    exit 1
fi
echo "[OK] $(python3 --version)"

# ── clean ─────────────────────────────────────────────────────────
if [[ "$TARGET" == "clean" ]]; then
    echo "[INFO] Removing build/ and dist/ ..."
    rm -rf "$PROJECT_ROOT/build" "$PROJECT_ROOT/dist" "$PROJECT_ROOT/__pycache__"
    echo "[OK] Clean done."
    exit 0
fi

# ── virtualenv ────────────────────────────────────────────────────
if [[ ! -f "$VENV_DIR/bin/activate" ]]; then
    echo "[INFO] Creating virtualenv at $VENV_DIR ..."
    python3 -m venv "$VENV_DIR"
fi
echo "[INFO] Activating virtualenv..."
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# ── install deps ──────────────────────────────────────────────────
echo "[INFO] Installing runtime dependencies..."
pip install --quiet --upgrade pip
pip install --quiet -r "$PROJECT_ROOT/requirements.txt"

echo "[INFO] Installing build dependencies..."
pip install --quiet -r "$PROJECT_ROOT/requirements-build.txt"

# ── clean previous dist ───────────────────────────────────────────
rm -rf "$PROJECT_ROOT/build" "$PROJECT_ROOT/dist"

cd "$PROJECT_ROOT"

# ── helper functions ──────────────────────────────────────────────
build_exe() {
    echo
    echo "[STEP] Building standalone exe folder (build_exe)..."
    python setup.py build_exe
    echo "[OK] Output: dist/exe/"
}

build_dmg() {
    if [[ "$(uname -s)" != "Darwin" ]]; then
        echo "[WARN] bdist_dmg is only available on macOS. Skipping."
        return 0
    fi
    echo
    echo "[STEP] Building macOS DMG bundle (bdist_dmg)..."
    pip install --quiet dmgbuild
    python setup.py bdist_dmg
    echo "[OK] DMG generated in dist/"
}

build_pyinstaller() {
    echo
    echo "[STEP] Building via PyInstaller..."
    ADD_DATA_SEP=":"   # Linux/macOS use colon
    pyinstaller --noconfirm \
        --onefile \
        --windowed \
        --name "Picture" \
        --add-data "src${ADD_DATA_SEP}src" \
        --collect-all pymupdf \
        --hidden-import fitz \
        main.py
    echo "[OK] Binary: dist/Picture"
}

# ── dispatch ──────────────────────────────────────────────────────
case "$TARGET" in
    all)
        build_exe
        build_dmg
        ;;
    exe)
        build_exe
        ;;
    dmg)
        build_dmg
        ;;
    pyinstaller)
        build_pyinstaller
        ;;
    *)
        echo "[ERROR] Unknown target: $TARGET"
        echo "        Valid targets: all  exe  dmg  pyinstaller  clean"
        exit 1
        ;;
esac

echo
echo " ========================================="
echo "  Build complete. Artifacts in: dist/"
echo " ========================================="
echo
