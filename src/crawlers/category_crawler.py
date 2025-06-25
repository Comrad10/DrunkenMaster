import json
import asyncio
from typing import List, Dict
from playwright.async_api import Page
from src.crawlers.base_crawler import BaseCrawler
from src.parsers.search_results_parser import SearchResultsParser
from src.utils import logger
from src.config import config

class CategoryCrawler(BaseCrawler):
    def __init__(self, category: str):
        super().__init__()
        self.category = category
        self.parser = SearchResultsParser()
        self.products = []
        self.api_token = None
        self.search_endpoint = None
        
    async def _extract_api_config(self, page: Page):
        try:
            api_config = await page.evaluate("""
                () => {
                    if (window.Coveo && window.Coveo.SearchEndpoint) {
                        return {
                            token: window.Coveo.SearchEndpoint.endpoints.default.options.accessToken,
                            endpoint: window.Coveo.SearchEndpoint.endpoints.default.options.restUri,
                            queryPipeline: window.Coveo.SearchEndpoint.endpoints.default.options.queryPipeline
                        };
                    }
                    return null;
                }
            """)
            
            if api_config:
                self.api_token = api_config.get('token')
                self.search_endpoint = api_config.get('endpoint')
                logger.info(f"Extracted API config - Token: {self.api_token[:20]}...")
                return True
            
        except Exception as e:
            logger.error(f"Error extracting API config: {e}")
        
        return False
    
    async def _intercept_search_response(self, response):
        if ("platform.cloud.coveo.com" in response.url and "search" in response.url) and response.status == 200:
            try:
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    logger.info(f"Intercepted search API: {response.url}")
                    
                    # Skip query suggestions, focus on actual search results
                    if "querySuggest" in response.url:
                        logger.debug("Skipping query suggestion endpoint")
                        return
                    
                    body = await response.body()
                    data = json.loads(body)
                    
                    logger.info(f"Response data keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    
                    # Save the raw response for debugging
                    if isinstance(data, dict) and 'results' in data:
                        logger.info(f"Found {len(data.get('results', []))} results in response")
                        
                        # Save sample response for debugging
                        debug_file = config.DATA_DIR / f"debug_response_{self.category}.json"
                        with open(debug_file, 'w') as f:
                            json.dump(data, f, indent=2)
                        logger.info(f"Saved debug response to: {debug_file}")
                    
                    products = self.parser.parse_coveo_response(data)
                    if products:
                        self.products.extend(products)
                        logger.info(f"Captured {len(products)} products from API response")
                        
                        pagination = self.parser.parse_pagination_info(data)
                        logger.info(f"Total products available: {pagination['total_count']}")
                    else:
                        logger.warning("No products found in API response")
                        if isinstance(data, dict):
                            logger.debug(f"Response structure: {list(data.keys())}")
                        
            except Exception as e:
                logger.error(f"Error intercepting search response: {e}")
                logger.debug(f"Response URL: {response.url}")
                logger.debug(f"Response status: {response.status}")
    
    async def crawl_with_pagination(self, page: Page, max_pages: int = None):
        current_page = 0
        has_more = True
        
        while has_more and (max_pages is None or current_page < max_pages):
            try:
                if current_page > 0:
                    load_more_selectors = [
                        'button[aria-label*="Load more"]',
                        'button[class*="load-more"]',
                        '.CoveoResultsPerPage button',
                        'button:has-text("Load More")'
                    ]
                    
                    clicked = False
                    for selector in load_more_selectors:
                        try:
                            button = await page.wait_for_selector(selector, timeout=3000)
                            if button and await button.is_visible():
                                await button.click()
                                await page.wait_for_timeout(2000)
                                clicked = True
                                break
                        except:
                            continue
                    
                    if not clicked:
                        try:
                            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                            await page.wait_for_timeout(2000)
                        except:
                            pass
                
                await page.wait_for_timeout(1000)
                
                current_page += 1
                logger.info(f"Processed page {current_page} for category: {self.category}")
                
                if current_page >= 5:
                    has_more = False
                    
            except Exception as e:
                logger.error(f"Error during pagination: {e}")
                has_more = False
    
    async def crawl(self):
        page = await self.create_page()
        
        page.on("response", self._intercept_search_response)
        
        try:
            # First, go to the main products page to load the search interface
            if await self.safe_navigate(page, config.LCBO_PRODUCTS_URL):
                
                await page.wait_for_timeout(5000)  # Give more time to load
                
                await self._extract_api_config(page)
                
                # Now search for the category
                try:
                    # Look for search box and enter category
                    search_selectors = [
                        'input[type="search"]',
                        'input[placeholder*="search" i]',
                        '.CoveoSearchbox input',
                        '#search-input',
                        '.search-input'
                    ]
                    
                    searched = False
                    for selector in search_selectors:
                        try:
                            search_input = await page.wait_for_selector(selector, timeout=3000)
                            if search_input and await search_input.is_visible():
                                await search_input.fill(self.category)
                                await search_input.press("Enter")
                                logger.info(f"Searched for category: {self.category}")
                                searched = True
                                break
                        except:
                            continue
                    
                    if not searched:
                        logger.warning("Could not find search box, trying direct URL")
                        category_url = f"{config.LCBO_PRODUCTS_URL}?q={self.category}"
                        await self.safe_navigate(page, category_url)
                    
                    await page.wait_for_timeout(3000)
                    
                except Exception as e:
                    logger.error(f"Error performing search: {e}")
                
                await self.crawl_with_pagination(page, max_pages=3)  # Get a few pages
                
                logger.info(f"Total products collected for {self.category}: {len(self.products)}")
                
                unique_products = self._deduplicate_products()
                logger.info(f"Unique products after deduplication: {len(unique_products)}")
                
                return unique_products
                
        except Exception as e:
            logger.error(f"Error crawling category {self.category}: {e}")
            return []
            
        finally:
            await page.close()
    
    def _deduplicate_products(self) -> List[Dict]:
        seen_ids = set()
        unique_products = []
        
        for product in self.products:
            lcbo_id = product.get('lcbo_id')
            if lcbo_id and lcbo_id not in seen_ids:
                seen_ids.add(lcbo_id)
                unique_products.append(product)
        
        return unique_products
    
    async def run(self) -> List[Dict]:
        try:
            products = await self.crawl()
            return products
        finally:
            await self.close()