# Google Search MCP Server

A Python MCP (Model Context Protocol) server that performs Google searches with anti-detection techniques using Playwright.

## Features

- **Real browser automation** - Uses Playwright/Chromium to avoid bot detection
- **User agent rotation** - Random desktop user agents
- **Stealth mode** - Hides webdriver fingerprint
- **Rate limiting** - 3-8 second delays between requests
- **Proxy rotation ready** - Fetches and validates free proxies

## Installation

```bash
# Clone and setup
cd Web Search MCP

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
python -m playwright install chromium
```

### Adding to OpenCode

Add to your OpenCode config at `~/.config/opencode/opencode.json`:

```json
{
  "mcp": {
    "google-search-mcp": {
      "type": "local",
      "command": [
        "E:\\Projects\\OSP\\Web Search MCP\\.venv\\Scripts\\python.exe",
        "E:\\Projects\\OSP\\Web Search MCP\\server.py"
      ],
      "environment": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

Restart OpenCode - the `google_search_tool` will be available.

## Usage

### As MCP Server

Run with stdio transport:

```bash
python server.py
```

### Using the Tool

In OpenCode or any MCP client:

```
google_search "python tutorials" num_results=5 lang=en
```

### Programmatic Usage

```python
import asyncio
from server import google_search

async def main():
    results = await google_search("python", num_results=5)
    for r in results:
        print(f"{r.title}: {r.url}")

asyncio.run(main())
```

## Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| query | str | required | Search query |
| num_results | int | 10 | Max results (<=100) |
| lang | str | "en" | Language code |

## Anti-Detection Techniques

| Technique | Implementation |
|-----------|---------------|
| Browser automation | Playwright/Chromium |
| UA rotation | 8 realistic Chrome/Firefox UAs |
| Stealth scripts | Hides `navigator.webdriver` |
| Rate limiting | Random 3-8s delays + 0-3s jitter |
| Proxy support | Fetches from proxifly CDN |

## Requirements

- Python 3.10+
- [Playwright](https://playwright.dev/python/)
- Chrome/Chromium browser

## License

MIT