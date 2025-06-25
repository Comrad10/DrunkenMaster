import json
import asyncio
from playwright.async_api import Page
from src.crawlers.base_crawler import BaseCrawler
from src.utils import logger
from src.config import config

class CoveoAPIInvestigator(BaseCrawler):
    def __init__(self):
        super().__init__()
        self.api_calls = []
        self.access_token = None
        self.api_endpoints = {}
        
    async def _intercept_requests(self, route, request):
        if "coveo" in request.url:
            logger.info(f"Intercepted Coveo request: {request.url}")
            headers = request.headers
            
            if "authorization" in headers:
                self.access_token = headers["authorization"]
                logger.info(f"Found access token: {self.access_token[:20]}...")
            
            self.api_calls.append({
                "url": request.url,
                "method": request.method,
                "headers": headers,
                "post_data": request.post_data if request.method == "POST" else None
            })
        
        await route.continue_()
    
    async def _intercept_responses(self, response):
        if "coveo" in response.url and response.status == 200:
            try:
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    body = await response.body()
                    data = json.loads(body)
                    
                    endpoint_type = self._identify_endpoint_type(response.url, data)
                    if endpoint_type:
                        self.api_endpoints[endpoint_type] = {
                            "url": response.url,
                            "sample_response": self._truncate_response(data)
                        }
                        logger.info(f"Identified {endpoint_type} endpoint: {response.url}")
                        
            except Exception as e:
                logger.error(f"Error processing response: {e}")
    
    def _identify_endpoint_type(self, url, data):
        if "/search" in url:
            return "search"
        elif "/product" in url:
            return "product_detail"
        elif "/analytics" in url:
            return "analytics"
        elif "/facet" in url:
            return "facets"
        return None
    
    def _truncate_response(self, data, max_items=3):
        if isinstance(data, dict):
            truncated = {}
            for key, value in list(data.items())[:10]:
                if isinstance(value, list) and len(value) > max_items:
                    truncated[key] = value[:max_items] + ["...truncated"]
                elif isinstance(value, dict):
                    truncated[key] = self._truncate_response(value, max_items)
                else:
                    truncated[key] = value
            return truncated
        return data
    
    async def crawl(self):
        page = await self.create_page()
        
        await page.route("**/*", self._intercept_requests)
        page.on("response", self._intercept_responses)
        
        try:
            await self.safe_navigate(page, config.LCBO_PRODUCTS_URL)
            
            await page.wait_for_timeout(5000)
            
            search_selectors = [
                'input[type="search"]',
                'input[placeholder*="search" i]',
                '.CoveoSearchbox',
                '#search-input'
            ]
            
            for selector in search_selectors:
                try:
                    await page.wait_for_selector(selector, timeout=2000)
                    await page.fill(selector, "wine")
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(3000)
                    break
                except:
                    continue
            
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(2000)
            
            try:
                product_selector = '.product-tile, .product-card, [class*="product"]'
                products = await page.query_selector_all(product_selector)
                if products:
                    await products[0].click()
                    await page.wait_for_timeout(3000)
            except:
                logger.warning("Could not click on product")
            
            self._analyze_findings()
            
        finally:
            await page.close()
    
    def _analyze_findings(self):
        logger.info("\n=== Coveo API Investigation Results ===")
        logger.info(f"Total API calls intercepted: {len(self.api_calls)}")
        logger.info(f"Access token found: {'Yes' if self.access_token else 'No'}")
        logger.info(f"Endpoints discovered: {list(self.api_endpoints.keys())}")
        
        if self.api_calls:
            logger.info("\nSample API calls:")
            for call in self.api_calls[:3]:
                logger.info(f"  - {call['method']} {call['url'][:100]}...")
        
        investigation_report = {
            "access_token": self.access_token,
            "endpoints": self.api_endpoints,
            "sample_calls": self.api_calls[:5]
        }
        
        with open(config.DATA_DIR / "coveo_api_investigation.json", "w") as f:
            json.dump(investigation_report, f, indent=2)
            logger.info(f"\nInvestigation report saved to: {f.name}")
    
    async def run(self):
        try:
            await self.crawl()
        finally:
            await self.close()