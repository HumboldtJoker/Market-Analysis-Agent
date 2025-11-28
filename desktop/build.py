"""
AutoInvestor Desktop Build Script
Packages the application into a standalone executable using PyInstaller
"""

import os
import sys
import shutil
import subprocess

# Directories
DESKTOP_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(DESKTOP_DIR)
BUILD_DIR = os.path.join(DESKTOP_DIR, 'build')
DIST_DIR = os.path.join(DESKTOP_DIR, 'dist')


def check_dependencies():
    """Check and install required build dependencies"""
    deps = ['pyinstaller', 'pywebview', 'flask', 'flask-cors']

    for dep in deps:
        try:
            __import__(dep.replace('-', '_'))
        except ImportError:
            print(f"Installing {dep}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', dep])


def create_spec_file():
    """Create PyInstaller spec file"""
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

import os
import sys

block_cipher = None

# Collect all Python files from project root
project_root = r'{PROJECT_ROOT}'
desktop_dir = r'{DESKTOP_DIR}'

# Data files to include
datas = [
    (os.path.join(desktop_dir, 'templates'), 'templates'),
    (os.path.join(desktop_dir, 'static'), 'static'),
]

# Hidden imports for dynamic imports
hidden_imports = [
    'flask',
    'flask_cors',
    'webview',
    'anthropic',
    'yfinance',
    'pandas',
    'numpy',
    'requests',
    'fredapi',
    'chromadb',
    'sentence_transformers',
]

# Collect all project modules
project_modules = []
for f in os.listdir(project_root):
    if f.endswith('.py') and not f.startswith('test_'):
        module = f[:-3]
        project_modules.append(module)

hidden_imports.extend(project_modules)

a = Analysis(
    [os.path.join(desktop_dir, 'launcher.py')],
    pathex=[project_root, desktop_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AutoInvestor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if desired
)
'''
    spec_path = os.path.join(DESKTOP_DIR, 'AutoInvestor.spec')
    with open(spec_path, 'w') as f:
        f.write(spec_content)
    return spec_path


def build():
    """Run the build process"""
    print("=" * 60)
    print("AutoInvestor Desktop Build")
    print("=" * 60)

    # Check dependencies
    print("\n[1/4] Checking dependencies...")
    check_dependencies()

    # Clean previous builds
    print("\n[2/4] Cleaning previous builds...")
    for d in [BUILD_DIR, DIST_DIR]:
        if os.path.exists(d):
            shutil.rmtree(d)

    # Create spec file
    print("\n[3/4] Creating build specification...")
    spec_path = create_spec_file()

    # Run PyInstaller
    print("\n[4/4] Building executable (this may take a few minutes)...")
    result = subprocess.run(
        [sys.executable, '-m', 'PyInstaller', spec_path, '--clean'],
        cwd=DESKTOP_DIR,
        capture_output=False
    )

    if result.returncode == 0:
        exe_path = os.path.join(DIST_DIR, 'AutoInvestor.exe')
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print("\n" + "=" * 60)
            print("BUILD SUCCESSFUL!")
            print("=" * 60)
            print(f"\nExecutable: {exe_path}")
            print(f"Size: {size_mb:.1f} MB")
            print("\nTo run: double-click AutoInvestor.exe")
            print("\nNote: Set environment variables before running:")
            print("  - ANTHROPIC_API_KEY (required for AI analysis)")
            print("  - RAPIDAPI_KEY (optional, for Congress data)")
            print("  - FRED_API_KEY (optional, for macro data)")
        else:
            print("\nBuild completed but executable not found.")
    else:
        print("\nBuild failed! Check the output above for errors.")

    return result.returncode


def dev():
    """Run in development mode (without building)"""
    print("Starting in development mode...")
    print("Press Ctrl+C to stop\n")

    # Add paths
    sys.path.insert(0, PROJECT_ROOT)
    sys.path.insert(0, DESKTOP_DIR)

    # Import and run launcher
    from launcher import main
    main()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'dev':
        dev()
    else:
        sys.exit(build())
