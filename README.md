# Google Search MCP Server

An MCP server that searches Google and returns results as structured data, with no API key and no signup.

It drives a real Chromium browser through Playwright rather than scraping an endpoint, which is what keeps it working when the obvious approaches start returning consent pages.

## Tool

### google_search_tool

| Argument | Type | Default | Description |
| --- | --- | --- | --- |
| `query` | string | required | What to search for |
| `num_results` | int | `10` | How many results to return, capped at 100 |
| `lang` | string | `en` | Language code for the results page |

Each result carries a `title` and a `url`. The `summary` field is present in the schema but is currently empty, because the snippet is not scraped yet.

## How it avoids detection

- Runs a real browser through Playwright instead of calling an endpoint
- Rotates between eight desktop user agent strings
- Applies a stealth script that hides `navigator.webdriver`
- Waits for the page to settle before reading the results
- Sleeps between requests, with jitter, so the request rate stays human
- Unwraps Google's `/url?q=` redirect to hand back the real destination

Proxy rotation is wired in and pulls free proxies from the proxifly CDN. It is off by default.

## Requirements

- Python 3.10 or newer
- Playwright with a Chromium build

## Install

```bash
git clone https://github.com/hussainbiedouh/google-search-mcp-no-api-key.git
cd google-search-mcp-no-api-key

python -m venv .venv
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # macOS and Linux

pip install -r requirements.txt
python -m playwright install chromium
```

The Playwright browser download is separate from the pip install and is easy to miss. Without it the server starts and then fails on the first search.

## Add it to your client

The server speaks stdio, so the client starts it. Ready-made snippets are in [`mcp-configs/`](mcp-configs), and each client expects a different key:

| Client | Config file | Key |
| --- | --- | --- |
| OpenCode | `~/.config/opencode/opencode.jsonc` | `mcp.servers` |
| Claude Desktop | `claude_desktop_config.json` | `mcpServers` |
| Cursor | `~/.cursor/mcp.json` | `mcpServers` |
| VS Code | `.vscode/mcp.json` | `servers` |

For OpenCode:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "servers": {
      "google-search-mcp": {
        "type": "local",
        "command": [
          "C:\\path\\to\\google-search-mcp-no-api-key\\.venv\\Scripts\\python.exe",
          "server.py"
        ],
        "environment": {
          "PYTHONIOENCODING": "utf-8"
        }
      }
    }
  }
}
```

Point the command at the full path of the interpreter. The PATH a client inherits is not always the PATH in your shell, and `python` can resolve to a different install than the one you tested with.

The same file will not work across clients, because the key differs. [mcp-client-config](https://github.com/hussainbiedouh/mcp-client-config) has the full table and what each failure mode looks like.

## Calling it

From an agent, ask for something like:

```
Use google_search_tool to find the current release notes for Playwright.
```

## Running it by hand

```bash
python server.py
```

The server speaks MCP on stdin and stdout, so running it in a terminal and typing will not do anything useful. Point a client at it instead.

## Tests

```bash
python test_server.py
```

## License

MIT
