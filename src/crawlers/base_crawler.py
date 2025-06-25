import asyncio
from abc import ABC, abstractmethod
from playwright.async_api import async_playwright, Browser, Page
from src.utils import logger, RateLimiter, UserAgentRotator
from src.config import config

class BaseCrawler(ABC):
    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.user_agent_rotator = UserAgentRotator()
        self.browser = None
        self.context = None
        
    async def setup_browser(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        
    async def create_page(self) -> Page:
        if not self.browser:
            await self.setup_browser()
            
        context = await self.browser.new_context(
            user_agent=self.user_agent_rotator.get_random(),
            viewport={'width': 1920, 'height': 1080},
            locale='en-CA'
        )
        
        page = await context.new_page()
        
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false
            });
        """)
        
        page.on("response", self._handle_response)
        
        return page
    
    async def _handle_response(self, response):
        if "coveo" in response.url and response.status == 200:
            try:
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    logger.debug(f"Coveo API response: {response.url}")
            except Exception as e:
                logger.error(f"Error handling response: {e}")
    
    async def close(self):
        if self.browser:
            await self.browser.close()
    
    @abstractmethod
    async def crawl(self):
        pass
    
    async def safe_navigate(self, page: Page, url: str, wait_for_selector=None):
        try:
            self.rate_limiter.wait()
            logger.info(f"Navigating to: {url}")
            
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            if wait_for_selector:
                await page.wait_for_selector(wait_for_selector, timeout=10000)
                
            self.rate_limiter.reset_backoff()
            return True
            
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            self.rate_limiter.increase_backoff()
            return False