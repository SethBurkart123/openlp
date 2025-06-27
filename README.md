# OpenLP - Open Source Lyrics Projection

**This is a fork of OpenLP with added MCP control capabilities for AI models.**

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

### 🤖 AI Control via MCP Plugin (New!)

This fork introduces an MCP (Model Context Protocol) plugin that allows AI models to fully control OpenLP programmatically. **The MCP plugin is disabled by default** and must be manually enabled in the plugin settings.

#### MCP Plugin Features:
- **Complete Service Management**: Create, load, save, and manipulate services
- **Smart Media Handling**: Automatic media type detection and proper plugin routing
- **PowerPoint/PDF Support**: Auto-conversion of presentations with LibreOffice fallback
- **Live Control**: Real-time slide navigation and theme switching
- **URL Support**: Automatic download of media files, services, and themes from URLs
- **Email Processing**: Parse emails to automatically create services
- **Theme Management**: Create, modify, and apply themes programmatically
- **Structured Data Import**: Build services from structured data sources

#### Supported Media Types:
- **Images**: JPG, PNG, GIF, SVG, WebP (via Images plugin)
- **Videos**: MP4, AVI, MOV, WMV, etc. (via Media plugin)
- **Audio**: MP3, WAV, OGG, FLAC, etc. (via Media plugin)
- **Presentations**: PDF, PowerPoint (.pptx, .ppt), OpenDocument (.odp)
- **Services**: OpenLP service files (.osz)
- **Themes**: Background images for theme creation

#### URL Support:
The MCP plugin automatically downloads files from URLs including:
- Direct file links (http/https/ftp/ftps)
- Video platforms (YouTube, Vimeo, etc.)
- Modern web services without traditional file extensions
- Intelligent Content-Type detection

## Installation

### Requirements
- Python 3.10 or higher
- PySide6 (Qt6) GUI framework
- Various platform-specific dependencies (see pyproject.toml)

### Standard Installation
```bash
# Clone this repository
git clone https://github.com/sethburkart123/openlp.git
cd openlp

# Install dependencies
pip install -r requirements.txt

# Run OpenLP
python run_openlp.py
```

### MCP Plugin Setup

The MCP plugin requires the `fastmcp` library:

```bash
pip install fastmcp
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
    "openlp-control": {
      "transport": {
        "type": "sse",
        "url": "http://127.0.0.1:8765/sse"
      }
    }
  }
}
```

2. Restart Claude Desktop
3. The MCP server will be available when the plugin is enabled

## Usage

### Basic OpenLP Usage
- Create a new service or load an existing one
- Add songs, media, and presentations to your service
- Use the live display to project content
- Customize themes and layouts as needed

### AI Control Examples

Once the MCP plugin is enabled and connected to an AI model, you can:

**Create a complete service:**
```
"Create a new service with:
1. Welcome slide with church name
2. Three worship songs about grace
3. A sermon slide titled 'Finding Hope'
4. Closing song
Apply a blue gradient theme to everything."
```

**Add media from URLs:**
```
"Add this image to the service: https://unsplash.com/photos/church-interior
Then add this video: https://www.youtube.com/watch?v=LRP8d7hhpoQ"
```

**Control live display:**
```
"Make the second service item live, then advance to the next slide"
```

**Process email content:**
```
"Create a service from this email: [paste email content]
Extract the song list and create appropriate slides"
```

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

