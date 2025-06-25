import asyncio
from typing import Dict, Optional, List
from playwright.async_api import Page
from src.crawlers.base_crawler import BaseCrawler
from src.parsers.product_parser import ProductParser
from src.utils import logger
from src.config import config

class ProductCrawler(BaseCrawler):
    def __init__(self):
        super().__init__()
        self.parser = ProductParser()
        
    async def crawl_product(self, product_url: str) -> Optional[Dict]:
        page = await self.create_page()
        
        try:
            if not await self.safe_navigate(page, product_url):
                return None
            
            await page.wait_for_timeout(2000)
            
            await self._wait_for_product_load(page)
            
            html = await page.content()
            
            product_data = self.parser.parse_from_page(html)
            
            if not product_data:
                product_data = await self._extract_from_javascript(page)
            
            if product_data:
                product_data['product_url'] = product_url
                
                inventory_data = await self._extract_inventory(page)
                if inventory_data:
                    product_data['inventory'] = inventory_data
                
                logger.info(f"Successfully crawled product: {product_data.get('name', 'Unknown')}")
                return product_data
            else:
                logger.warning(f"Could not extract product data from: {product_url}")
                return None
                
        except Exception as e:
            logger.error(f"Error crawling product {product_url}: {e}")
            return None
            
        finally:
            await page.close()
    
    async def _wait_for_product_load(self, page: Page):
        selectors = [
            '.product-name',
            'h1[class*="product"]',
            '.product-details',
            '[class*="price"]'
        ]
        
        for selector in selectors:
            try:
                await page.wait_for_selector(selector, timeout=5000)
                break
            except:
                continue
    
    async def _extract_from_javascript(self, page: Page) -> Optional[Dict]:
        try:
            product_data = await page.evaluate("""
                () => {
                    // Try to find product data in various places
                    
                    // Check for structured data
                    const ldJson = document.querySelector('script[type="application/ld+json"]');
                    if (ldJson) {
                        try {
                            const data = JSON.parse(ldJson.textContent);
                            if (data['@type'] === 'Product') {
                                return {
                                    name: data.name,
                                    brand: data.brand?.name,
                                    description: data.description,
                                    image_url: data.image,
                                    price: data.offers?.price
                                };
                            }
                        } catch (e) {}
                    }
                    
                    // Check for product object in window
                    if (window.product || window.productData) {
                        return window.product || window.productData;
                    }
                    
                    // Extract from meta tags
                    const getMetaContent = (property) => {
                        const meta = document.querySelector(`meta[property="${property}"], meta[name="${property}"]`);
                        return meta?.content;
                    };
                    
                    return {
                        name: getMetaContent('og:title') || document.title,
                        description: getMetaContent('og:description'),
                        image_url: getMetaContent('og:image'),
                        product_url: getMetaContent('og:url')
                    };
                }
            """)
            
            if product_data and any(product_data.values()):
                return product_data
                
        except Exception as e:
            logger.debug(f"Could not extract JavaScript data: {e}")
        
        return None
    
    async def _extract_inventory(self, page: Page) -> Optional[Dict]:
        try:
            inventory_data = await page.evaluate("""
                () => {
                    const inventory = {};
                    
                    // Check for stock status
                    const stockElements = document.querySelectorAll('[class*="stock"], [class*="availability"], [class*="inventory"]');
                    for (const elem of stockElements) {
                        const text = elem.textContent.toLowerCase();
                        if (text.includes('in stock') || text.includes('available')) {
                            inventory.in_stock = true;
                        } else if (text.includes('out of stock') || text.includes('unavailable')) {
                            inventory.in_stock = false;
                        }
                    }
                    
                    // Check for online availability
                    const onlineElements = document.querySelectorAll('[class*="online"], [class*="delivery"]');
                    for (const elem of onlineElements) {
                        const text = elem.textContent.toLowerCase();
                        if (text.includes('available')) {
                            inventory.online_available = true;
                        }
                    }
                    
                    // Check for quantity
                    const qtyElements = document.querySelectorAll('[class*="quantity"], [class*="stock-level"]');
                    for (const elem of qtyElements) {
                        const match = elem.textContent.match(/\\d+/);
                        if (match) {
                            inventory.quantity = parseInt(match[0]);
                        }
                    }
                    
                    return Object.keys(inventory).length > 0 ? inventory : null;
                }
            """)
            
            return inventory_data
            
        except Exception as e:
            logger.debug(f"Could not extract inventory data: {e}")
            return None
    
    async def crawl_multiple(self, product_urls: List[str], max_concurrent: int = 3) -> List[Dict]:
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def crawl_with_semaphore(url):
            async with semaphore:
                return await self.crawl_product(url)
        
        tasks = [crawl_with_semaphore(url) for url in product_urls]
        results = await asyncio.gather(*tasks)
        
        return [r for r in results if r is not None]
    
    async def crawl(self):
        pass