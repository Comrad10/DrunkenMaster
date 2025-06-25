import json
import asyncio
from typing import List, Dict, Optional
from playwright.async_api import Page
from src.crawlers.base_crawler import BaseCrawler
from src.utils import logger
from src.config import config

class ProductInventoryCrawler(BaseCrawler):
    """Crawler to investigate store-specific inventory data for individual products"""
    
    def __init__(self):
        super().__init__()
        
    async def _intercept_inventory_responses(self, response):
        """Intercept API responses that might contain store inventory data"""
        if response.status == 200:
            try:
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    # Check if this looks like an inventory or store-related API
                    url_lower = response.url.lower()
                    if any(keyword in url_lower for keyword in ['inventory', 'store', 'availability', 'stock']):
                        body = await response.body()
                        data = json.loads(body)
                        
                        logger.info(f"Intercepted potential inventory API: {response.url}")
                        
                        # Save the raw response for analysis
                        debug_file = config.DATA_DIR / f"debug_inventory_{response.url.split('/')[-1]}.json"
                        with open(debug_file, 'w') as f:
                            json.dump(data, f, indent=2)
                        logger.info(f"Saved inventory debug response to: {debug_file}")
                        
            except Exception as e:
                logger.debug(f"Error intercepting inventory response: {e}")
    
    async def investigate_product_inventory(self, lcbo_id: str, store_ids: List[str] = None) -> Dict:
        """Investigate store-specific inventory for a product"""
        page = await self.create_page()
        page.on("response", self._intercept_inventory_responses)
        
        try:
            # Navigate to product page
            product_url = f"{config.LCBO_BASE_URL}/en/products/lcbo-{lcbo_id}"
            
            if await self.safe_navigate(page, product_url):
                await page.wait_for_timeout(3000)
                
                # Look for store availability section
                availability_data = await self._extract_store_availability(page, lcbo_id, store_ids)
                
                # Try to interact with store selector if available
                store_selector_data = await self._try_store_selector(page, lcbo_id, store_ids)
                
                return {
                    'lcbo_id': lcbo_id,
                    'product_url': product_url,
                    'availability_data': availability_data,
                    'store_selector_data': store_selector_data,
                    'investigation_timestamp': asyncio.get_event_loop().time()
                }
                
        except Exception as e:
            logger.error(f"Error investigating product {lcbo_id} inventory: {e}")
            return {'lcbo_id': lcbo_id, 'error': str(e)}
            
        finally:
            await page.close()
    
    async def _extract_store_availability(self, page: Page, lcbo_id: str, store_ids: List[str] = None) -> Dict:
        """Extract store availability information from product page"""
        availability_data = {}
        
        try:
            # Look for various store availability indicators
            availability_selectors = [
                '[class*="availability"]',
                '[class*="store"]',
                '[class*="inventory"]',
                '[class*="stock"]',
                '.store-availability',
                '#store-availability',
                '.product-availability'
            ]
            
            for selector in availability_selectors:
                try:
                    elements = await page.query_selector_all(selector)
                    if elements:
                        logger.info(f"Found {len(elements)} availability elements with selector: {selector}")
                        
                        for i, element in enumerate(elements):
                            text_content = await element.text_content()
                            if text_content and text_content.strip():
                                availability_data[f'{selector}_{i}'] = text_content.strip()
                        
                except Exception as e:
                    logger.debug(f"Error with availability selector {selector}: {e}")
                    continue
            
            # Look for specific store mentions
            if store_ids:
                page_content = await page.content()
                for store_id in store_ids:
                    if store_id in page_content:
                        availability_data[f'store_{store_id}_mentioned'] = True
                        
        except Exception as e:
            logger.error(f"Error extracting store availability: {e}")
        
        return availability_data
    
    async def _try_store_selector(self, page: Page, lcbo_id: str, store_ids: List[str] = None) -> Dict:
        """Try to interact with store selector/locator on product page"""
        store_selector_data = {}
        
        try:
            # Look for store selector elements
            store_selector_candidates = [
                'select[name*="store"]',
                'select[id*="store"]',
                '.store-selector',
                '#store-selector',
                'button[class*="store"]',
                'button[id*="store"]',
                '[class*="store-locator"]',
                '[class*="find-store"]'
            ]
            
            for selector in store_selector_candidates:
                try:
                    element = await page.wait_for_selector(selector, timeout=2000)
                    if element and await element.is_visible():
                        logger.info(f"Found store selector: {selector}")
                        
                        # Try to interact with it
                        if 'select' in selector:
                            # For select elements, get options
                            options = await page.query_selector_all(f'{selector} option')
                            store_selector_data['selector_type'] = 'select'
                            store_selector_data['options'] = []
                            for option in options:
                                option_text = await option.text_content()
                                option_value = await option.get_attribute('value')
                                if option_text:
                                    store_selector_data['options'].append({
                                        'text': option_text.strip(),
                                        'value': option_value
                                    })
                        else:
                            # For buttons/other elements, try clicking
                            store_selector_data['selector_type'] = 'clickable'
                            await element.click()
                            await page.wait_for_timeout(2000)
                            
                            # Look for any new content that appears
                            new_content = await self._extract_store_availability(page, lcbo_id, store_ids)
                            store_selector_data['after_click'] = new_content
                        
                        break
                        
                except Exception as e:
                    logger.debug(f"Could not interact with store selector {selector}: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"Error trying store selector: {e}")
        
        return store_selector_data
    
    async def investigate_multiple_products(self, lcbo_ids: List[str], store_ids: List[str] = None) -> List[Dict]:
        """Investigate store inventory for multiple products"""
        results = []
        
        for lcbo_id in lcbo_ids:
            logger.info(f"Investigating product {lcbo_id}...")
            result = await self.investigate_product_inventory(lcbo_id, store_ids)
            results.append(result)
            
            # Rate limiting
            await asyncio.sleep(self.rate_limiter.min_delay)
        
        return results
    
    async def crawl(self):
        """Main crawl method - investigate multiple products"""
        # Default behavior: investigate a few products
        sample_products = ['42702', '139667', '42638']
        st_catharines_stores = ['522', '392', '115', '189', '343']
        
        return await self.investigate_multiple_products(sample_products, st_catharines_stores)