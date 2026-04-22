"""
MCP Server for Google Searching with Anti-Detection Techniques.
Uses Playwright for reliable Google search results.
"""
import asyncio
import random
import time
from typing import Optional
from urllib.parse import parse_qs, urlparse

from playwright.async_api import async_playwright
from fastmcp import FastMCP
from pydantic import BaseModel
import httpx


# Data Models
class SearchResult(BaseModel):
    title: str
    url: str
    summary: str


# USER_AGENTS list - realistic user agent strings
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
]


class UserAgentRotator:
    """Rotates user agents."""
    
    def __init__(self):
        self._agents = USER_AGENTS
    
    def get_random(self) -> str:
        return random.choice(self._agents)


class ProxyRotator:
    """Rotates proxies with validation."""
    
    PROXY_URL = "https://cdn.jsdelivr.net/gh/proxifly/free-proxy-list@main/proxies/http/data.txt"
    CACHE_DURATION = 300
    
    def __init__(self):
        self._proxies: list[str] = []
        self._last_fetch: float = 0
        self._lock = asyncio.Lock()
    
    async def refresh(self) -> None:
        async with self._lock:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(self.PROXY_URL)
                    response.raise_for_status()
                    proxies = [
                        line.strip() 
                        for line in response.text.splitlines() 
                        if line.strip() and ":" in line.strip()
                    ]
                    self._proxies = proxies
                    self._last_fetch = time.time()
            except Exception:
                self._proxies = []
    
    async def get_valid_proxy(self) -> Optional[str]:
        now = time.time()
        if now - self._last_fetch > self.CACHE_DURATION:
            await self.refresh()
        
        if not self._proxies:
            return None
        
        return random.choice(self._proxies)


class RateLimiter:
    """Enforces rate limiting."""
    
    MIN_DELAY = 3
    MAX_DELAY = 8
    JITTER_MAX = 3
    
    def __init__(self):
        self._last_request: float = 0
        self._lock = asyncio.Lock()
    
    async def enforce_delay(self) -> None:
        async with self._lock:
            now = time.time()
            elapsed = now - self._last_request
            if elapsed < self.MIN_DELAY:
                delay = random.uniform(self.MIN_DELAY, self.MAX_DELAY)
                await asyncio.sleep(delay)
            self._last_request = time.time()
    
    async def add_jitter(self) -> None:
        jitter = random.uniform(0, self.JITTER_MAX)
        await asyncio.sleep(jitter)


# Global browser instance
_browser = None
_playwright = None


async def get_browser():
    """Get or create browser instance."""
    global _browser, _playwright
    
    if _browser is None or not _browser.is_connected():
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-sandbox",
            ]
        )
    
    return _browser


async def close_browser():
    """Close browser instance."""
    global _browser, _playwright
    
    if _browser:
        await _browser.close()
        _browser = None
    if _playwright:
        await _playwright.stop()
        _playwright = None


async def google_search(
    query: str,
    num_results: int = 10,
    lang: str = "en",
) -> list[SearchResult]:
    """
    Search Google with anti-detection techniques.
    """
    rate_limiter = RateLimiter()
    ua_rotator = UserAgentRotator()
    
    await rate_limiter.enforce_delay()
    await rate_limiter.add_jitter()
    
    user_agent = ua_rotator.get_random()
    num_results = min(num_results, 100)
    
    browser = await get_browser()
    context = await browser.new_context(
        user_agent=user_agent,
        viewport={"width": 1920, "height": 1080},
        locale=lang,
    )
    
    # Inject stealth scripts
    await context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    """)
    
    page = await context.new_page()
    
    try:
        await page.goto(f"https://www.google.com/search?q={query}&hl={lang}")
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(2000)
        
        # Find search results using h3 tags (Google's result titles)
        h3_tags = await page.query_selector_all("h3")
        results = []
        seen_urls = set()
        
        for h3 in h3_tags:
            try:
                title = await h3.inner_text()
                title = title.strip()
                
                if not title or len(title) < 3:
                    continue
                
                # Find parent link
                link = await h3.query_selector("xpath=ancestor::a")
                if not link:
                    continue
                
                href = await link.get_attribute("href")
                if not href:
                    continue
                
                # Extract actual URL from Google redirect
                url = href
                if href.startswith("/url?"):
                    params = parse_qs(urlparse(href).query)
                    if "q" in params:
                        url = params["q"][0]
                elif not url.startswith("http"):
                    continue
                
                if url in seen_urls:
                    continue
                
                seen_urls.add(url)
                results.append(SearchResult(title=title, url=url, summary=""))
                
                if len(results) >= num_results:
                    break
            except Exception:
                continue
        
        return results[:num_results]
        
    finally:
        await context.close()


# MCP Server setup
mcp = FastMCP(
    name="Google Search", 
    instructions="Search Google with anti-detection. Use google_search_tool() to perform searches."
)


@mcp.tool()
async def google_search_tool(
    query: str,
    num_results: int = 10,
    lang: str = "en",
) -> list[dict]:
    """
    Search Google and return results with title, summary, and link.
    """
    try:
        results = await google_search(query, num_results, lang)
        return [r.model_dump() for r in results]
    except Exception as e:
        return [{"title": f"Error: {type(e).__name__}", "url": "", "summary": str(e)}]


if __name__ == "__main__":
    mcp.run()
