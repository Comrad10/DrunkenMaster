import json
import asyncio
from typing import List, Dict, Optional
from playwright.async_api import Page
from src.crawlers.base_crawler import BaseCrawler
from src.utils import logger
from src.config import config
from src.storage import StoreStorage

class StoreInventoryCrawler(BaseCrawler):
    """Enhanced crawler to get store-specific inventory data using LCBO's store selection API"""
    
    def __init__(self):
        super().__init__()
        self.store_storage = StoreStorage()
        self.store_api_responses = {}
        
    async def _intercept_store_inventory_responses(self, response):
        """Intercept store selection and inventory API responses"""
        if response.status == 200:
            try:
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    url_lower = response.url.lower()
                    
                    # Store selection API
                    if 'storepickup/selection/store' in url_lower:
                        body = await response.body()
                        data = json.loads(body)
                        logger.info(f"Intercepted store selection API: {response.url}")
                        
                        # Extract store info from URL parameters
                        if 'value=' in response.url:
                            store_param = response.url.split('value=')[1].split('&')[0]
                            self.store_api_responses[store_param] = data
                        
                        # Save debug data
                        debug_file = config.DATA_DIR / f"store_selection_{store_param}.json"
                        with open(debug_file, 'w') as f:
                            json.dump(data, f, indent=2)
                    
                    # Product availability API  
                    elif any(keyword in url_lower for keyword in ['product', 'availability', 'stock', 'inventory']):
                        body = await response.body()
                        data = json.loads(body)
                        logger.info(f"Intercepted product availability API: {response.url}")
                        
                        # Save debug data
                        debug_file = config.DATA_DIR / f"product_availability_{len(self.store_api_responses)}.json"
                        with open(debug_file, 'w') as f:
                            json.dump(data, f, indent=2)
                        
            except Exception as e:
                logger.debug(f"Error intercepting store inventory response: {e}")
    
    async def check_product_at_stores(self, lcbo_id: str, store_ids: List[str] = None) -> Dict:
        """Check product availability at specific stores"""
        if not store_ids:
            # Get St. Catharines store IDs
            store_ids = ['522', '392', '115', '189', '343']
        
        page = await self.create_page()
        page.on("response", self._intercept_store_inventory_responses)
        
        results = {
            'lcbo_id': lcbo_id,
            'stores_checked': [],
            'availability': {}
        }
        
        try:
            # Navigate to product page
            product_url = f"{config.LCBO_BASE_URL}/en/products/lcbo-{lcbo_id}"
            
            if await self.safe_navigate(page, product_url):
                await page.wait_for_timeout(3000)
                
                # Get the LCBO internal store identifiers for our stores
                store_mappings = await self._get_store_mappings(store_ids)
                
                for store_id in store_ids:
                    logger.info(f"Checking product {lcbo_id} at store {store_id}")
                    
                    # Try to select the store and check availability
                    availability = await self._check_store_availability(page, lcbo_id, store_id, store_mappings.get(store_id))
                    
                    results['stores_checked'].append(store_id)
                    results['availability'][store_id] = availability
                    
                    # Rate limiting between stores
                    await asyncio.sleep(2)
                
        except Exception as e:
            logger.error(f"Error checking product {lcbo_id} at stores: {e}")
            results['error'] = str(e)
            
        finally:
            await page.close()
        
        return results
    
    async def _get_store_mappings(self, store_ids: List[str]) -> Dict[str, str]:
        """Get LCBO internal store identifiers for our store IDs"""
        mappings = {}
        
        # Known mappings for St. Catharines stores
        # These may need to be discovered through the store locator API
        known_mappings = {
            '522': '522',  # Geneva & Scott
            '392': '392',  # Vansickle & Fourth  
            '115': '115',  # Lakeshore Road
            '189': '189',  # King Street
            '343': '343'   # Glendale & Merritt
        }
        
        for store_id in store_ids:
            mappings[store_id] = known_mappings.get(store_id, store_id)
        
        return mappings
    
    async def _check_store_availability(self, page: Page, lcbo_id: str, store_id: str, internal_store_id: str) -> Dict:
        """Check availability of product at a specific store"""
        availability = {
            'store_id': store_id,
            'in_stock': False,
            'pickup_available': False,
            'error': None
        }
        
        try:
            # Look for store selector elements
            store_selector_found = False
            
            # Try different selectors for the store selection mechanism
            selectors_to_try = [
                '#my_store',
                '.my_store',
                '[class*="store-select"]',
                '[class*="store-picker"]',
                'button[class*="store"]'
            ]
            
            for selector in selectors_to_try:
                try:
                    element = await page.wait_for_selector(selector, timeout=3000)
                    if element and await element.is_visible():
                        logger.info(f"Found store selector: {selector}")
                        
                        # Click to open store selector
                        await element.click()
                        await page.wait_for_timeout(2000)
                        
                        # Look for change store or find store options
                        change_store_selectors = [
                            'text="Change Store"',
                            'text="Find Another Store"', 
                            '[class*="change-store"]',
                            '[class*="find-store"]'
                        ]
                        
                        for change_selector in change_store_selectors:
                            try:
                                change_element = await page.wait_for_selector(change_selector, timeout=2000)
                                if change_element and await change_element.is_visible():
                                    await change_element.click()
                                    await page.wait_for_timeout(2000)
                                    store_selector_found = True
                                    break
                            except:
                                continue
                        
                        if store_selector_found:
                            break
                            
                except Exception as e:
                    logger.debug(f"Could not use selector {selector}: {e}")
                    continue
            
            if store_selector_found:
                # Try to search for our specific store
                availability.update(await self._search_for_store(page, store_id, internal_store_id))
            else:
                # Fallback: check current page for availability indicators
                availability.update(await self._check_current_page_availability(page))
                
        except Exception as e:
            logger.error(f"Error checking store {store_id} availability: {e}")
            availability['error'] = str(e)
        
        return availability
    
    async def _search_for_store(self, page: Page, store_id: str, internal_store_id: str) -> Dict:
        """Search for and select a specific store"""
        result = {'search_attempted': True}
        
        try:
            # Look for search input in store locator
            search_inputs = [
                'input[placeholder*="postal" i]',
                'input[placeholder*="search" i]',
                'input[type="search"]',
                '#store-search',
                '.store-search input'
            ]
            
            for search_input_selector in search_inputs:
                try:
                    search_input = await page.wait_for_selector(search_input_selector, timeout=2000)
                    if search_input and await search_input.is_visible():
                        # Search for St. Catharines
                        await search_input.fill("St. Catharines, ON")
                        await search_input.press("Enter")
                        await page.wait_for_timeout(3000)
                        
                        # Look for store with our ID in the results
                        store_found = await self._select_store_from_results(page, store_id)
                        result.update(store_found)
                        break
                        
                except Exception as e:
                    logger.debug(f"Could not use search input {search_input_selector}: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"Error searching for store: {e}")
            result['search_error'] = str(e)
        
        return result
    
    async def _select_store_from_results(self, page: Page, store_id: str) -> Dict:
        """Select our target store from search results"""
        result = {'store_selected': False}
        
        try:
            # Look for store results containing our store ID or known names
            store_names = {
                '522': 'Geneva & Scott',
                '392': 'Vansickle & Fourth', 
                '115': 'Lakeshore Road',
                '189': 'King Street',
                '343': 'Glendale & Merritt'
            }
            
            target_name = store_names.get(store_id, store_id)
            
            # Try to find and click on our store
            store_selectors = [
                f'text="{target_name}"',
                f'[data-store-id="{store_id}"]',
                f'text="{store_id}"'
            ]
            
            for selector in store_selectors:
                try:
                    store_element = await page.wait_for_selector(selector, timeout=2000)
                    if store_element:
                        await store_element.click()
                        await page.wait_for_timeout(3000)
                        
                        # Check if store was selected and get availability
                        availability = await self._check_current_page_availability(page)
                        result.update(availability)
                        result['store_selected'] = True
                        break
                        
                except Exception as e:
                    logger.debug(f"Could not select store with {selector}: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"Error selecting store from results: {e}")
            result['selection_error'] = str(e)
        
        return result
    
    async def _check_current_page_availability(self, page: Page) -> Dict:
        """Check current page for product availability indicators"""
        availability = {
            'in_stock': False,
            'pickup_available': False,
            'online_available': False
        }
        
        try:
            # Look for availability indicators
            page_content = await page.content()
            content_lower = page_content.lower()
            
            # Check for positive availability indicators
            positive_indicators = [
                'in stock',
                'available',
                'pickup available', 
                'same-day pickup',
                'ready for pickup'
            ]
            
            # Check for negative availability indicators  
            negative_indicators = [
                'out of stock',
                'not available',
                'unavailable',
                'pickup not available'
            ]
            
            # Count positive vs negative indicators
            positive_count = sum(1 for indicator in positive_indicators if indicator in content_lower)
            negative_count = sum(1 for indicator in negative_indicators if indicator in content_lower)
            
            if positive_count > negative_count:
                availability['in_stock'] = True
                
            if 'pickup' in content_lower and 'available' in content_lower:
                availability['pickup_available'] = True
                
            if 'online' in content_lower and 'available' in content_lower:
                availability['online_available'] = True
                
            # Look for specific availability text elements
            availability_elements = await page.query_selector_all('[class*="availability"], [class*="stock"], .product-availability')
            for element in availability_elements:
                text = await element.text_content()
                if text and text.strip():
                    text_lower = text.lower()
                    if 'available' in text_lower or 'in stock' in text_lower:
                        availability['in_stock'] = True
                    if 'pickup' in text_lower and 'available' in text_lower:
                        availability['pickup_available'] = True
                        
        except Exception as e:
            logger.debug(f"Error checking page availability: {e}")
            availability['check_error'] = str(e)
        
        return availability
    
    async def crawl(self):
        """Main crawl method - check multiple products at St. Catharines stores"""
        sample_products = ['42702', '139667', '42638']
        st_catharines_stores = ['522', '392', '115', '189', '343']
        
        results = []
        for product_id in sample_products:
            result = await self.check_product_at_stores(product_id, st_catharines_stores)
            results.append(result)
        
        return results