# OpenLP - Open Source Lyrics Projection

**This is a fork of OpenLP with added MCP control capabilities for AI models and some other minor tweaks.**

## Overview

OpenLP is a free, open-source application for churches and other religious organizations to project lyrics, presentations, and media during worship services. This fork adds powerful AI integration through the Model Context Protocol (MCP), allowing AI models to automatically control OpenLP and create services from various sources.

## Features

### Core OpenLP Features
- **Lyrics Projection**: Display song lyrics with customizable themes
- **Multimedia Support**: Images, videos, audio files, and presentations
- **Bible Integration**: Multiple Bible versions and translations
- **Service Management**: Create, organize, and manage worship services
- **Live Display Control**: Real-time control of slides and media
- **Theme Customization**: Custom fonts, colors, backgrounds, and layouts
- **Multi-display Support**: Separate displays for stage and audience

## Installation

### Requirements
- Python 3.10 or higher

### Standard Installation
```bash
# Clone this repository
git clone https://github.com/sethburkart123/openlp.git
cd openlp

# Install dependencies
pip install -e .

# Run OpenLP
python run_openlp.py
```

#### Enabling the MCP Plugin:
1. Launch OpenLP
2. Go to **Settings** → **Plugins**
3. Find **MCP Plugin** in the list
4. Check the box to enable it
5. Restart OpenLP

#### Connecting with Claude Desktop:
1. Add this configuration to your Claude Desktop config file:
```json
{
  "mcpServers": {
    "openlp": {
      "command": "npx",
      "args": ["mcp-remote", "http://localhost:8765/sse", "--allow-http"]
    }
  }
}
```

2. Restart Claude Desktop
3. The MCP server will be available when the plugin is enabled

### Building

#### macOS

First install pyenchant with brew:
```bash
brew install pyenchant
```

Then build the app:
```bash
cd ./packaging/builders && export PYENCHANT_LIBRARY_PATH=/opt/homebrew/lib/libenchant-2.2.dylib && uv run macos-builder.py --config ../macos/config.ini --skip-update
```

## Development

### Project Structure
```
openlp/
├── core/           # Core OpenLP functionality
├── plugins/        # Plugin system
│   ├── mcp/        # MCP plugin
│   ├── songs/      # Song management
│   ├── media/      # Media files
│   └── ...
├── resources/      # UI resources and themes
└── tests/         # Test suite
```

### Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Known Limitations

- PowerPoint conversion may cause temporary GUI responsiveness issues
- Requires LibreOffice for optimal PowerPoint to PDF conversion
- MCP plugin is single-threaded and may block on large operations
- URL downloads are cached temporarily but cleaned up on shutdown, also freezes the UI during download

## License

This project is licensed under the GNU General Public License v3.0 or later - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Original OpenLP development team
- FastMCP library for MCP implementation

## Support

For issues related to:
- **Core OpenLP functionality**: Check the [official OpenLP documentation](https://openlp.org/)
- **MCP plugin**: Open an issue in this repository
- **AI integration**: Ensure your AI model supports MCP and is properly configured

