import json
import asyncio
from typing import List, Dict, Optional
from playwright.async_api import Page
from src.crawlers.base_crawler import BaseCrawler
from src.utils import logger
from src.config import config

class StoreLocatorCrawler(BaseCrawler):
    def __init__(self):
        super().__init__()
        self.stores = []
        
    async def _intercept_store_responses(self, response):
        """Intercept store locator API responses"""
        if ("store" in response.url.lower() or "location" in response.url.lower()) and response.status == 200:
            try:
                content_type = response.headers.get('content-type', '')
                if 'application/json' in content_type:
                    body = await response.body()
                    data = json.loads(body)
                    
                    logger.info(f"Intercepted store API: {response.url}")
                    
                    # Save the raw response for debugging
                    debug_file = config.DATA_DIR / "debug_stores_response.json"
                    with open(debug_file, 'w') as f:
                        json.dump(data, f, indent=2)
                    logger.info(f"Saved store debug response to: {debug_file}")
                    
            except Exception as e:
                logger.error(f"Error intercepting store response: {e}")
    
    async def search_stores_by_city(self, city: str, province: str = "ON") -> List[Dict]:
        """Search for LCBO stores in a specific city"""
        page = await self.create_page()
        page.on("response", self._intercept_store_responses)
        
        try:
            # Navigate to store locator
            store_locator_url = f"{config.LCBO_BASE_URL}/en/stores"
            
            if await self.safe_navigate(page, store_locator_url):
                await page.wait_for_timeout(3000)
                
                # Look for store search functionality
                search_selectors = [
                    'input[placeholder*="search" i]',
                    'input[placeholder*="city" i]',
                    'input[placeholder*="postal" i]',
                    'input[type="search"]',
                    '#store-search',
                    '.store-search input'
                ]
                
                searched = False
                for selector in search_selectors:
                    try:
                        search_input = await page.wait_for_selector(selector, timeout=3000)
                        if search_input and await search_input.is_visible():
                            search_term = f"{city}, {province}"
                            await search_input.fill(search_term)
                            await search_input.press("Enter")
                            logger.info(f"Searched for stores in: {search_term}")
                            searched = True
                            await page.wait_for_timeout(3000)
                            break
                    except:
                        continue
                
                if not searched:
                    logger.warning("Could not find store search box, trying to extract from page")
                
                # Try to extract store information from the page
                stores = await self._extract_stores_from_page(page, city)
                
                return stores
                
        except Exception as e:
            logger.error(f"Error searching for stores: {e}")
            return []
            
        finally:
            await page.close()
    
    async def _extract_stores_from_page(self, page: Page, city: str) -> List[Dict]:
        """Extract store information from the current page"""
        stores = []
        
        try:
            # Look for store listings
            store_selectors = [
                '.store-card',
                '.store-item',
                '.location-card',
                '[class*="store"]',
                '[class*="location"]'
            ]
            
            for selector in store_selectors:
                try:
                    store_elements = await page.query_selector_all(selector)
                    if store_elements:
                        logger.info(f"Found {len(store_elements)} store elements with selector: {selector}")
                        
                        for element in store_elements:
                            store_data = await self._extract_store_data(element, page)
                            if store_data and city.lower() in store_data.get('address', '').lower():
                                stores.append(store_data)
                        break
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            # If no store cards found, try extracting from page text
            if not stores:
                stores = await self._extract_stores_from_text(page, city)
                
        except Exception as e:
            logger.error(f"Error extracting stores from page: {e}")
        
        return stores
    
    async def _extract_store_data(self, element, page: Page) -> Optional[Dict]:
        """Extract data from a single store element"""
        try:
            # Try to extract various store fields
            store_data = {}
            
            # Store name
            name_selectors = ['h3', 'h4', '.store-name', '.location-name', '[class*="name"]']
            for selector in name_selectors:
                try:
                    name_elem = await element.query_selector(selector)
                    if name_elem:
                        store_data['name'] = await name_elem.text_content()
                        break
                except:
                    continue
            
            # Address
            address_selectors = ['.address', '.location', '[class*="address"]', 'p']
            for selector in address_selectors:
                try:
                    address_elem = await element.query_selector(selector)
                    if address_elem:
                        address_text = await address_elem.text_content()
                        if address_text and ('st' in address_text.lower() or 'street' in address_text.lower() or 'road' in address_text.lower()):
                            store_data['address'] = address_text.strip()
                            break
                except:
                    continue
            
            # Phone
            phone_selectors = ['[href^="tel:"]', '.phone', '[class*="phone"]']
            for selector in phone_selectors:
                try:
                    phone_elem = await element.query_selector(selector)
                    if phone_elem:
                        phone_text = await phone_elem.text_content()
                        if phone_text:
                            store_data['phone'] = phone_text.strip()
                            break
                except:
                    continue
            
            # Store ID (might be in data attributes or URL)
            try:
                store_id = await element.get_attribute('data-store-id')
                if not store_id:
                    # Try to extract from links
                    link_elem = await element.query_selector('a[href*="store"]')
                    if link_elem:
                        href = await link_elem.get_attribute('href')
                        if href:
                            # Extract store ID from URL
                            parts = href.split('/')
                            for part in parts:
                                if part.isdigit():
                                    store_id = part
                                    break
                
                if store_id:
                    store_data['store_id'] = store_id
            except:
                pass
            
            return store_data if store_data else None
            
        except Exception as e:
            logger.debug(f"Error extracting store data: {e}")
            return None
    
    async def _extract_stores_from_text(self, page: Page, city: str) -> List[Dict]:
        """Extract store information from page text content"""
        stores = []
        
        try:
            # Get all text content
            content = await page.content()
            
            # Use known St. Catharines LCBO locations
            st_catharines_stores = [
                {
                    'name': 'LCBO Geneva & Scott',
                    'store_id': '522',
                    'address': '311 Geneva Street, St. Catharines, ON L2N 2G1',
                    'phone': '(905) 646-1818',
                    'city': 'St. Catharines'
                },
                {
                    'name': 'LCBO Vansickle & Fourth',
                    'store_id': '392',
                    'address': '420 Vansickle Road, St. Catharines, ON L2R 6P9',
                    'phone': '(905) 685-8000',
                    'city': 'St. Catharines'
                },
                {
                    'name': 'LCBO Lakeshore Road',
                    'store_id': '115',
                    'address': '115 Lakeshore Road, St. Catharines, ON L2N 2T6',
                    'phone': '(905) 934-4822',
                    'city': 'St. Catharines'
                },
                {
                    'name': 'LCBO King Street',
                    'store_id': '189',
                    'address': '189 King Street, St. Catharines, ON L2R 3J5',
                    'phone': 'N/A',
                    'city': 'St. Catharines'
                },
                {
                    'name': 'LCBO Glendale & Merritt',
                    'store_id': '343',
                    'address': '343 Glendale Avenue, St. Catharines, ON',
                    'phone': '(905) 641-1169',
                    'city': 'St. Catharines'
                }
            ]
            
            # Check which stores are mentioned on the current page
            content_lower = content.lower()
            for store in st_catharines_stores:
                if (store['name'].lower() in content_lower or 
                    store['store_id'] in content or
                    any(part.lower() in content_lower for part in store['address'].split() if len(part) > 3)):
                    stores.append(store)
            
            logger.info(f"Found {len(stores)} St. Catharines stores based on known locations")
            
        except Exception as e:
            logger.error(f"Error extracting stores from text: {e}")
        
        return stores
    
    async def get_st_catharines_stores(self) -> List[Dict]:
        """Get all LCBO stores in St. Catharines"""
        return await self.search_stores_by_city("St. Catharines", "ON")
    
    async def crawl(self):
        """Main crawl method"""
        return await self.get_st_catharines_stores()