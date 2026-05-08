@echo off
setlocal EnableDelayedExpansion

REM ===================================================================
REM  build.bat  –  Picture build script (Windows)
REM
REM  Usage
REM  -----
REM    build.bat            →  build all targets (exe + MSI)
REM    build.bat exe        →  standalone folder only  (dist\exe\)
REM    build.bat msi        →  Windows MSI installer   (dist\*.msi)
REM    build.bat pyinstaller→  single-file EXE via PyInstaller (dist\Picture.exe)
REM    build.bat clean      →  remove build/ and dist/
REM ===================================================================

set "PROJECT_ROOT=%~dp0"
set "VENV_DIR=%PROJECT_ROOT%.venv"
set "PYTHON=python"
set "TARGET=%~1"
if "%TARGET%"=="" set "TARGET=all"

echo.
echo  =========================================
echo   Picture – Build Script (Windows)
echo   Target : %TARGET%
echo  =========================================
echo.

REM ── 0. Check Python ───────────────────────────────────────────────
%PYTHON% --version >nul 2>&1
if not errorlevel 1 goto :python_ok

REM Python not in PATH – search common installation directories
if exist "C:\ProgramData\miniconda3\python.exe" (
    set "PYTHON=C:\ProgramData\miniconda3\python.exe"
    goto :python_ok
)
if exist "%USERPROFILE%\miniconda3\python.exe" (
    set "PYTHON=%USERPROFILE%\miniconda3\python.exe"
    goto :python_ok
)
if exist "%USERPROFILE%\anaconda3\python.exe" (
    set "PYTHON=%USERPROFILE%\anaconda3\python.exe"
    goto :python_ok
)
if exist "C:\ProgramData\anaconda3\python.exe" (
    set "PYTHON=C:\ProgramData\anaconda3\python.exe"
    goto :python_ok
)
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
    if exist "%%D\python.exe" (
        set "PYTHON=%%D\python.exe"
        goto :python_ok
    )
)
echo [ERROR] Python n'est pas trouve dans le PATH.
echo         Installez Python 3.10+ depuis https://python.org
exit /b 1

:python_ok
for /f "tokens=*" %%V in ('%PYTHON% --version 2^>^&1') do set "PY_VER=%%V"
echo [OK] %PY_VER%

REM ── clean target ─────────────────────────────────────────────────
if /i "%TARGET%"=="clean" (
    echo [INFO] Nettoyage des dossiers build et dist...
    if exist "%PROJECT_ROOT%build"     rmdir /s /q "%PROJECT_ROOT%build"
    if exist "%PROJECT_ROOT%dist"      rmdir /s /q "%PROJECT_ROOT%dist"
    if exist "%PROJECT_ROOT%__pycache__" rmdir /s /q "%PROJECT_ROOT%__pycache__"
    echo [OK] Nettoyage terminé.
    goto :end
)

REM ── 1. Create / activate virtualenv ──────────────────────────────
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo [INFO] Création du virtualenv dans %VENV_DIR% ...
    %PYTHON% -m venv "%VENV_DIR%"
    if errorlevel 1 ( echo [ERROR] Echec création venv ; exit /b 1 )
)
echo [INFO] Activation du virtualenv...
call "%VENV_DIR%\Scripts\activate.bat"

REM ── 2. Install runtime deps ───────────────────────────────────────
echo [INFO] Installation des dépendances runtime...
python -m pip install --quiet --upgrade pip
pip install -r "%PROJECT_ROOT%requirements.txt"
if errorlevel 1 ( echo [ERROR] Echec pip install requirements.txt ; exit /b 1 )
echo [OK] Dépendances runtime installées.

REM ── 3. Install build deps ─────────────────────────────────────────
echo [INFO] Installation des dépendances de build...
pip install -r "%PROJECT_ROOT%requirements-build.txt"
if errorlevel 1 ( echo [ERROR] Echec pip install requirements-build.txt ; exit /b 1 )
echo [OK] Dépendances de build installées.

REM ── 4. Clean previous dist ────────────────────────────────────────
echo [INFO] Nettoyage des artefacts précédents...
if exist "%PROJECT_ROOT%build" rmdir /s /q "%PROJECT_ROOT%build"
if exist "%PROJECT_ROOT%dist"  rmdir /s /q "%PROJECT_ROOT%dist"

REM ── 5. Build ──────────────────────────────────────────────────────
cd /d "%PROJECT_ROOT%"

if /i "%TARGET%"=="exe" goto :build_exe
if /i "%TARGET%"=="msi" goto :build_msi
if /i "%TARGET%"=="pyinstaller" goto :build_pyinstaller
if /i "%TARGET%"=="all" goto :build_all

echo [ERROR] Cible inconnue : %TARGET%
echo         Cibles valides : all  exe  msi  pyinstaller  clean
exit /b 1

REM ── build_all ─────────────────────────────────────────────────────
:build_all
call :build_exe_fn
if errorlevel 1 exit /b 1
call :build_msi_fn
if errorlevel 1 exit /b 1
goto :success

REM ── build_exe ─────────────────────────────────────────────────────
:build_exe
call :build_exe_fn
if errorlevel 1 exit /b 1
goto :success

REM ── build_msi ─────────────────────────────────────────────────────
:build_msi
call :build_msi_fn
if errorlevel 1 exit /b 1
goto :success

REM ── build_pyinstaller ─────────────────────────────────────────────
:build_pyinstaller
call :build_pyinstaller_fn
if errorlevel 1 exit /b 1
goto :success

REM ── Functions ─────────────────────────────────────────────────────
:build_exe_fn
echo.
echo [STEP] Construction du dossier exécutable standalone (build_exe)...
python setup.py build_exe
if errorlevel 1 (
    echo [ERROR] build_exe a échoué.
    exit /b 1
)
echo [OK] Exécutable généré dans dist\exe\
exit /b 0

:build_msi_fn
echo.
echo [STEP] Construction de l'installateur MSI (bdist_msi)...
python setup.py bdist_msi
if errorlevel 1 (
    echo [ERROR] bdist_msi a échoué.
    exit /b 1
)
REM Move MSI from dist/ root to dist/installer/
if not exist "%PROJECT_ROOT%dist\installer" mkdir "%PROJECT_ROOT%dist\installer"
for %%F in ("%PROJECT_ROOT%dist\*.msi") do (
    move "%%F" "%PROJECT_ROOT%dist\installer\" >nul
    echo [OK] MSI déplacé vers dist\installer\%%~nxF
)
exit /b 0

:build_pyinstaller_fn
echo.
echo [STEP] Construction via PyInstaller (single-file EXE)...
pyinstaller --noconfirm ^
    --onefile ^
    --windowed ^
    --name "Picture" ^
    --add-data "src;src" ^
    --collect-all pymupdf ^
    --hidden-import fitz ^
    main.py
if errorlevel 1 (
    echo [ERROR] PyInstaller a échoué.
    exit /b 1
)
echo [OK] EXE généré dans dist\Picture.exe
exit /b 0

:success
echo.
echo  =========================================
echo   Build terminé avec succès.
echo   Artefacts dans : %PROJECT_ROOT%dist\
echo  =========================================
echo.

:end
endlocal
