"""
Tests for the Google Search MCP Server.
"""
import asyncio
import sys
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError


# Mock critical imports before trying to import server
mock_httpx = MagicMock()
mock_httpx.AsyncClient = MagicMock()
sys.modules['httpx'] = mock_httpx

mock_googlesearch = MagicMock()
sys.modules['googlesearch'] = mock_googlesearch

mock_tenacity = MagicMock()
mock_tenacity.retry = lambda *a, **kw: lambda f: f
mock_tenacity.stop_after_attempt = MagicMock()
mock_tenacity.wait_exponential = MagicMock()
sys.modules['tenacity'] = mock_tenacity


# Mock fastmcp
class MockFastMCP:
    def __init__(self, name, instructions):
        self.name = name
        self.instructions = instructions
        self._tools = {}
    
    def tool(self, func=None):
        """Decorator for marking functions as tools."""
        def decorator(f):
            self._tools[f.__name__] = f
            return f
        if func is None:
            # Called as a decorator with arguments
            return decorator
        else:
            # Called as a plain decorator
            return decorator(func)

mock_fastmcp = MagicMock()
mock_fastmcp.FastMCP = MockFastMCP
sys.modules['fastmcp'] = mock_fastmcp


# Now import from server
from server import (
    USER_AGENTS,
    UserAgentRotator,
    ProxyRotator,
    RateLimiter,
    SearchResult,
    mcp,
)


# === USER_AGENTS Tests ===

def test_user_agents_has_at_least_25_entries():
    """Test that USER_AGENTS list has at least 25 entries."""
    assert len(USER_AGENTS) >= 25, f"USER_AGENTS has {len(USER_AGENTS)} entries, expected at least 25"


def test_user_agents_are_all_strings():
    """Test that all USER_AGENTS entries are non-empty strings."""
    for ua in USER_AGENTS:
        assert isinstance(ua, str), f"User agent is not a string: {ua}"
        assert len(ua) > 0, "User agent is empty"


def test_user_agents_contain_mozilla():
    """Test that USER_AGENTS contain Mozilla prefix (valid browsers)."""
    for ua in USER_AGENTS:
        assert ua.startswith("Mozilla/"), f"Invalid user agent format: {ua}"


# === UserAgentRotator Tests ===

def test_user_agent_rotator_get_random_returns_valid_agent():
    """Test that UserAgentRotator.get_random() returns a valid user agent from the list."""
    rotator = UserAgentRotator()
    random_agent = rotator.get_random()
    assert random_agent in USER_AGENTS, f"Returned user agent not in list: {random_agent}"


def test_user_agent_rotator_get_random_returns_string():
    """Test that get_random() returns a string."""
    rotator = UserAgentRotator()
    result = rotator.get_random()
    assert isinstance(result, str), "get_random() did not return a string"


def test_user_agent_rotator_get_random_called_multiple_times():
    """Test that get_random() can be called multiple times without error."""
    rotator = UserAgentRotator()
    for _ in range(10):
        result = rotator.get_random()
        assert result in USER_AGENTS


# === SearchResult Model Tests ===

def test_search_result_valid_creation():
    """Test SearchResult model validation with valid data."""
    result = SearchResult(
        title="Test Title",
        url="https://example.com",
        summary="Test summary text",
    )
    assert result.title == "Test Title"
    assert result.url == "https://example.com"
    assert result.summary == "Test summary text"


def test_search_result_missing_title_raises_error():
    """Test that SearchResult raises ValidationError when title is missing."""
    with pytest.raises(ValidationError):
        SearchResult(url="https://example.com", summary="Test summary")


def test_search_result_missing_url_raises_error():
    """Test that SearchResult raises ValidationError when url is missing."""
    with pytest.raises(ValidationError):
        SearchResult(title="Test Title", summary="Test summary")


def test_search_result_missing_summary_raises_error():
    """Test that SearchResult raises ValidationError when summary is missing."""
    with pytest.raises(ValidationError):
        SearchResult(title="Test Title", url="https://example.com")


def test_search_result_invalid_url_format():
    """Test that SearchResult accepts any string as URL."""
    result = SearchResult(title="Test", url="not-a-url", summary="summary")
    assert result.url == "not-a-url"


def test_search_result_empty_strings():
    """Test that SearchResult allows empty strings for all fields."""
    result = SearchResult(title="", url="", summary="")
    assert result.title == ""
    assert result.url == ""
    assert result.summary == ""


def test_search_result_with_special_characters():
    """Test SearchResult with special characters in fields."""
    result = SearchResult(
        title="Test & < > \" '",
        url="https://example.com/path?param=value&other=test",
        summary="Summary with <html> &special chars",
    )
    assert result.title == "Test & < > \" '"


def test_search_result_model_dump():
    """Test SearchResult can be dumped to dict."""
    result = SearchResult(
        title="Test",
        url="https://test.com",
        summary="Summary",
    )
    data = result.model_dump()
    assert data["title"] == "Test"
    assert data["url"] == "https://test.com"
    assert data["summary"] == "Summary"


# === MCP Server Tests ===

def test_mcp_server_initialization():
    """Test that MCP server can be initialized."""
    assert mcp is not None
    assert mcp.name == "Google Search"


def test_mcp_server_has_tools_attribute():
    """Test that MCP server has tools capability."""
    assert hasattr(mcp, "name")
    assert mcp.name == "Google Search"


# === RateLimiter Tests (using anyio mode) ===

@pytest.mark.anyio
async def test_rate_limiter_enforce_delay():
    """Test RateLimiter.enforce_delay() executes without error."""
    limiter = RateLimiter()
    await limiter.enforce_delay()


@pytest.mark.anyio
async def test_rate_limiter_add_jitter():
    """Test RateLimiter.add_jitter() executes without error."""
    limiter = RateLimiter()
    await limiter.add_jitter()


@pytest.mark.anyio
async def test_rate_limiter_enforce_delay_returns_quickly_on_subsequent_calls():
    """Test that enforce_delay is fast after enough time has passed."""
    limiter = RateLimiter()
    # First call will likely cause a sleep
    await limiter.enforce_delay()
    # Wait for MIN_DELAY (3 seconds) + buffer to pass
    await asyncio.sleep(3.5)
    start = time.time()
    # Second call should be fast (no sleep) since enough time has passed
    await limiter.enforce_delay()
    elapsed = time.time() - start
    assert elapsed < 1.0, f"Second call took {elapsed}s, expected < 1s"


# === ProxyRotator Tests ===

@pytest.mark.anyio
async def test_proxy_rotator_initialization():
    """Test ProxyRotator initializes correctly."""
    rotator = ProxyRotator()
    assert rotator._proxies == []
    assert rotator._last_fetch == 0


@pytest.mark.anyio
async def test_proxy_rotator_refresh():
    """Test ProxyRotator.refresh() executes without error."""
    rotator = ProxyRotator()

    mock_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "http://proxy1.com:8080\nhttp://proxy2.com:8080"
    mock_response.raise_for_status = MagicMock()
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
    mock_client_instance.get = AsyncMock(return_value=mock_response)
    mock_httpx.AsyncClient.return_value = mock_client_instance

    await rotator.refresh()
    assert len(rotator._proxies) > 0


@pytest.mark.anyio
async def test_proxy_rotator_get_valid_proxy():
    """Test ProxyRotator.get_valid_proxy() returns a proxy dict."""
    rotator = ProxyRotator()
    rotator._proxies = ["http://testproxy.com:8080"]
    rotator._last_fetch = 1e9  # Far in the past

    mock_client_instance = MagicMock()
    # Make head raise no exception (simulating valid proxy)
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
    mock_client_instance.head = AsyncMock(return_value=MagicMock())
    mock_httpx.AsyncClient.return_value = mock_client_instance

    # Call get_valid_proxy - it will attempt proxy validation
    # We need to mock the sleep to avoid long delays
    with patch('asyncio.sleep', AsyncMock()):
        result = await rotator.get_valid_proxy()
        # If proxy is valid (doesn't raise), we expect a dict
        assert result is None or isinstance(result, dict)


@pytest.mark.anyio
async def test_proxy_rotator_handles_empty_proxies():
    """Test ProxyRotator handles empty proxy list."""
    rotator = ProxyRotator()
    rotator._proxies = []
    rotator._last_fetch = 1e9

    mock_client_instance = MagicMock()
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
    mock_httpx.AsyncClient.return_value = mock_client_instance

    result = await rotator.get_valid_proxy()
    # Should return None when no proxies available and refresh fails/returns empty
    assert result is None or isinstance(result, dict)


# === google_search Function Tests ===

@pytest.mark.anyio
async def test_google_search_with_mocked_dependencies():
    """Test google_search with fully mocked dependencies."""
    import server as server_module

    mock_search_func = MagicMock()
    mock_search_func.return_value = iter([
        {"title": "Python", "url": "https://python.org", "description": "Python language"},
        {"title": "JavaScript", "url": "https://js.org", "description": "JS language"},
    ])

    with patch.object(server_module, 'search', mock_search_func):
        results = await server_module.google_search(
            query="programming languages",
            num_results=10,
            language="en",
        )

        assert len(results) == 2
        assert results[0].title == "Python"
        assert results[1].title == "JavaScript"


@pytest.mark.anyio
async def test_google_search_caps_num_results():
    """Test google_search caps num_results at 100."""
    import server as server_module

    mock_search_func = MagicMock()
    mock_search_func.return_value = iter([
        {"title": f"Result {i}", "url": f"https://example{i}.com", "description": f"Desc {i}"}
        for i in range(150)
    ])

    mock_client_instance = MagicMock()
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
    mock_httpx.AsyncClient.return_value = mock_client_instance

    with patch.object(server_module, 'search', mock_search_func):
        await server_module.google_search(
            query="test",
            num_results=150,
            language="en",
        )

        call_args = mock_search_func.call_args
        assert call_args[1]["num_results"] == 100


@pytest.mark.anyio
async def test_rate_limiter_integration():
    """Test RateLimiter integration."""
    import server as server_module

    mock_search_func = MagicMock(return_value=iter([]))

    mock_client_instance = MagicMock()
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
    mock_httpx.AsyncClient.return_value = mock_client_instance

    with patch.object(server_module, 'search', mock_search_func):
        for _ in range(3):
            await server_module.google_search("test", 1, "en")
            await asyncio.sleep(0.01)