# Building OpenLP for macOS - Official Method

This guide uses the official OpenLP packaging scripts from [gitlab.com/openlp/packaging](https://gitlab.com/openlp/packaging).

## Prerequisites

### 1. Install System Dependencies
```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install required system packages
brew install pkg-config icu4c enchant

# Set up environment for ICU
export PATH="$PATH:/opt/homebrew/opt/icu4c/bin:/opt/homebrew/opt/icu4c/sbin"
export PKG_CONFIG_PATH="$PKG_CONFIG_PATH:/opt/homebrew/opt/icu4c/lib/pkgconfig"
```

### 2. Install Python Dependencies
```bash
# Install OpenLP in development mode
cd openlp
pip install -e .

# Install all macOS build dependencies
pip install \
    alembic \
    beautifulsoup4 \
    chardet \
    flask \
    flask-cors \
    lxml \
    Mako \
    mysql-connector-python \
    packaging \
    platformdirs \
    psycopg2-binary \
    pyenchant \
    PySide6 \
    pysword \
    pytest \
    pytest-qt \
    QDarkStyle \
    qrcode \
    QtAwesome \
    requests \
    six \
    sqlalchemy \
    waitress \
    websockets \
    py-applescript \
    pyobjc-core \
    pyobjc-framework-Cocoa \
    Pyro5 \
    PyInstaller \
    dmgbuild \
    macholib

# Install PyICU (needed for text processing)
pip install pyicu

# Set up spell checking support
export PYENCHANT_LIBRARY_PATH=/opt/homebrew/lib/libenchant-2.2.dylib
```

## Building OpenLP

The configuration has already been set up in `../packaging/macos/config.ini` with the correct path to your OpenLP source.

### Basic Build (Development)

For a development build using your current code:

```bash
cd ../packaging/builders
python macos-builder.py --config ../macos/config.ini --skip-update
```

### Release Build

For a release build of a specific version:

```bash
cd ../packaging/builders
python macos-builder.py --config ../macos/config.ini --release 3.1.0
```

## Command Line Options

The macOS builder supports these key options:

- `--config CONFIG_FILE` - Path to configuration file (required)
- `--release VERSION` - Build a specific release version (omit for development build)
- `--skip-update` - Don't update the source code (useful for development)
- `--verbose` - Show detailed output
- `--branch BRANCH_PATH` - Override branch path from config
- `--icon ICON_PATH` - Override icon path from config

## What Gets Built

The build process will:

1. Use PyInstaller to create the app bundle
2. Fix Qt library paths for macOS
3. Copy macOS-specific files (icon, Info.plist, etc.)
4. Install Pyro5 for LibreOffice integration
5. Create a DMG file for distribution

## Output

After successful build, you'll find:

- **App Bundle**: `packaging/builders/OpenLP-macOS/dist/OpenLP.app`
- **DMG File**: `packaging/builders/OpenLP-macOS/dist/OpenLP-{version}-{arch}.dmg`

## Testing

Test the built app:

```bash
# Run the app bundle directly
open ../packaging/builders/OpenLP-macOS/dist/OpenLP.app

# Or run from command line to see debug output
../packaging/builders/OpenLP-macOS/dist/OpenLP.app/Contents/MacOS/OpenLP
```

## Troubleshooting

### Build Fails
- Check that all Python dependencies are installed
- Ensure your OpenLP source code is working (can run `python run_openlp.py`)
- Use `--verbose` flag to see detailed error messages

### App Won't Start
- Run from command line to see error messages
- Check that PySide6 and all Qt components are properly installed
- Verify the config.ini paths are correct

### Code Signing (Optional)
To enable code signing, add your certificate to config.ini:
```ini
[codesigning]
certificate = Developer ID Application: Your Name
```

This approach uses the same build system that the OpenLP team uses for official releases, so it should be much more reliable than custom PyInstaller configurations! 