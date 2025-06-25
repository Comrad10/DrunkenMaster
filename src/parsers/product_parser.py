import re
from typing import Dict, Optional
from bs4 import BeautifulSoup
from src.utils import logger

class ProductParser:
    def __init__(self):
        self.price_pattern = re.compile(r'\$?([\d,]+\.?\d*)')
        self.volume_pattern = re.compile(r'(\d+)\s*(ml|mL|L|l)', re.IGNORECASE)
        self.alcohol_pattern = re.compile(r'(\d+\.?\d*)\s*%')
        
    def parse_from_page(self, html: str) -> Optional[Dict]:
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            product_data = {}
            
            product_data['name'] = self._extract_name(soup)
            product_data['brand'] = self._extract_brand(soup)
            product_data['price'] = self._extract_price(soup)
            product_data['volume_ml'] = self._extract_volume(soup)
            product_data['alcohol_percentage'] = self._extract_alcohol(soup)
            product_data['category'] = self._extract_category(soup)
            product_data['description'] = self._extract_description(soup)
            product_data['image_url'] = self._extract_image(soup)
            product_data['lcbo_id'] = self._extract_lcbo_id(soup)
            
            product_data.update(self._extract_metadata(soup))
            
            return product_data if product_data.get('lcbo_id') else None
            
        except Exception as e:
            logger.error(f"Error parsing product page: {e}")
            return None
    
    def parse_from_json(self, json_data: Dict) -> Optional[Dict]:
        try:
            product_data = {}
            
            product_data['lcbo_id'] = str(json_data.get('permanentid', ''))
            product_data['name'] = json_data.get('title', '')
            product_data['brand'] = json_data.get('ec_brand', '')
            product_data['price'] = self._parse_price(json_data.get('ec_price', 0))
            product_data['regular_price'] = self._parse_price(json_data.get('ec_promo_price', 0))
            product_data['category'] = json_data.get('ec_category', '')
            product_data['subcategory'] = json_data.get('ec_subcategory', '')
            product_data['image_url'] = json_data.get('ec_thumbnails', '')
            product_data['product_url'] = json_data.get('clickUri', '')
            
            raw_data = json_data.get('raw', {})
            product_data['volume_ml'] = self._parse_volume(raw_data.get('lcbounitvolume', ''))
            product_data['alcohol_percentage'] = self._parse_alcohol(raw_data.get('lcboalcoholpercent', ''))
            product_data['country'] = raw_data.get('lcbocountry', '')
            product_data['region'] = raw_data.get('lcboregion', '')
            product_data['description'] = raw_data.get('ec_description', '')
            
            return product_data if product_data.get('lcbo_id') else None
            
        except Exception as e:
            logger.error(f"Error parsing JSON data: {e}")
            return None
    
    def _extract_name(self, soup):
        selectors = [
            'h1.product-name',
            'h1[class*="product-title"]',
            'h1[class*="productName"]',
            '.product-details h1',
            'h1'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        return None
    
    def _extract_brand(self, soup):
        selectors = [
            '.product-brand',
            '[class*="brand"]',
            '.manufacturer',
            'span[itemprop="brand"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        return None
    
    def _extract_price(self, soup):
        selectors = [
            '.price-value',
            '.product-price',
            '[class*="price"]',
            'span[itemprop="price"]',
            '.prod-price'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                price_text = element.get_text(strip=True)
                return self._parse_price(price_text)
        return None
    
    def _extract_volume(self, soup):
        selectors = [
            '.product-volume',
            '.size',
            '[class*="volume"]',
            '[class*="size"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return self._parse_volume(element.get_text(strip=True))
        
        all_text = soup.get_text()
        return self._parse_volume(all_text)
    
    def _extract_alcohol(self, soup):
        selectors = [
            '.alcohol-content',
            '[class*="alcohol"]',
            '.abv'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return self._parse_alcohol(element.get_text(strip=True))
        
        all_text = soup.get_text()
        return self._parse_alcohol(all_text)
    
    def _extract_category(self, soup):
        breadcrumb = soup.select('.breadcrumb a, nav[aria-label="breadcrumb"] a')
        if breadcrumb and len(breadcrumb) > 1:
            return breadcrumb[1].get_text(strip=True)
        
        category_element = soup.select_one('.product-category, [class*="category"]')
        if category_element:
            return category_element.get_text(strip=True)
        
        return None
    
    def _extract_description(self, soup):
        selectors = [
            '.product-description',
            '[class*="description"]',
            '.tasting-notes',
            'div[itemprop="description"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        return None
    
    def _extract_image(self, soup):
        selectors = [
            'img.product-image',
            'img[class*="product"]',
            '.product-photo img',
            'img[itemprop="image"]'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                return element.get('src') or element.get('data-src')
        return None
    
    def _extract_lcbo_id(self, soup):
        url_element = soup.select_one('link[rel="canonical"], meta[property="og:url"]')
        if url_element:
            url = url_element.get('href') or url_element.get('content')
            match = re.search(r'/(\d+)(?:-|$)', url)
            if match:
                return match.group(1)
        
        sku_element = soup.select_one('[class*="sku"], [class*="product-id"], .itemNumber')
        if sku_element:
            text = sku_element.get_text(strip=True)
            match = re.search(r'\d+', text)
            if match:
                return match.group()
        
        return None
    
    def _extract_metadata(self, soup):
        metadata = {}
        
        info_pairs = soup.select('.product-info-item, .product-details-list li, .specifications tr')
        for item in info_pairs:
            text = item.get_text(strip=True).lower()
            if 'country' in text:
                metadata['country'] = self._clean_metadata_value(text)
            elif 'region' in text:
                metadata['region'] = self._clean_metadata_value(text)
            elif 'style' in text or 'type' in text:
                metadata['subcategory'] = self._clean_metadata_value(text)
        
        return metadata
    
    def _parse_price(self, price_str):
        if isinstance(price_str, (int, float)):
            return float(price_str)
        
        if not price_str:
            return None
            
        match = self.price_pattern.search(str(price_str))
        if match:
            return float(match.group(1).replace(',', ''))
        return None
    
    def _parse_volume(self, volume_str):
        if not volume_str:
            return None
            
        match = self.volume_pattern.search(str(volume_str))
        if match:
            volume = int(match.group(1))
            unit = match.group(2).lower()
            if unit in ['l', 'L']:
                volume *= 1000
            return volume
        return None
    
    def _parse_alcohol(self, alcohol_str):
        if not alcohol_str:
            return None
            
        match = self.alcohol_pattern.search(str(alcohol_str))
        if match:
            return float(match.group(1))
        return None
    
    def _clean_metadata_value(self, text):
        parts = text.split(':')
        if len(parts) > 1:
            return parts[1].strip()
        return text.strip()