import json
from typing import List, Dict, Optional
from src.utils import logger

class SearchResultsParser:
    def __init__(self):
        self.product_parser = None
        
    def parse_coveo_response(self, response_data: Dict) -> List[Dict]:
        try:
            products = []
            
            results = response_data.get('results', [])
            
            for result in results:
                product_data = self._extract_product_from_result(result)
                if product_data:
                    products.append(product_data)
            
            logger.info(f"Parsed {len(products)} products from Coveo response")
            return products
            
        except Exception as e:
            logger.error(f"Error parsing Coveo response: {e}")
            return []
    
    def _extract_product_from_result(self, result: Dict) -> Optional[Dict]:
        try:
            raw_data = result.get('raw', {})
            
            # Extract main product info
            product = {
                'lcbo_id': str(raw_data.get('permanentid', result.get('permanentid', ''))),
                'name': result.get('title', '').strip(),
                'brand': raw_data.get('ec_brand', ''),
                'price': self._safe_float(raw_data.get('ec_price')),
                'regular_price': self._safe_float(raw_data.get('ec_promo_price')),
                'image_url': raw_data.get('ec_thumbnails', ''),
                'product_url': result.get('clickUri', ''),
                'description': raw_data.get('ec_shortdesc', ''),
            }
            
            # Extract categories (take the most specific one)
            categories = raw_data.get('ec_category', [])
            if isinstance(categories, list) and categories:
                product_categories = [cat for cat in categories if cat.startswith('Products|')]
                if product_categories:
                    # Take the most specific product category
                    most_specific = max(product_categories, key=lambda x: x.count('|'))
                    parts = most_specific.split('|')
                    product['category'] = parts[1] if len(parts) > 1 else 'Unknown'
                    product['subcategory'] = parts[-1] if len(parts) > 2 else ''
                else:
                    product['category'] = categories[0] if categories else 'Unknown'
            
            # Extract additional product details
            if raw_data:
                product.update({
                    'volume_ml': self._parse_volume(raw_data.get('lcbo_unit_volume', '')),
                    'alcohol_percentage': self._safe_float(raw_data.get('lcbo_alcohol_percent')),
                    'country': raw_data.get('country_of_manufacture', ''),
                    'region': raw_data.get('lcbo_region_name', ''),
                    'tasting_notes': raw_data.get('lcbo_tastingnotes', ''),
                    'upc': raw_data.get('upc_number', ''),
                    'package_type': raw_data.get('lcbo_selling_package_name', ''),
                    'bottles_per_pack': raw_data.get('lcbo_bottles_per_pack', 1),
                    'loyalty_points': raw_data.get('loyalty_points', 0),
                })
            
            # Extract stock information
            product['in_stock'] = raw_data.get('out_of_stock', 'true').lower() == 'false'
            product['online_inventory'] = raw_data.get('online_inventory', 0)
            
            # Extract store inventory data for individual stores
            product['store_inventory'] = {
                'stores_stock': raw_data.get('stores_stock', 'false').lower() == 'true',
                'stores_stock_combined': raw_data.get('stores_stock_combined', 'false').lower() == 'true',
                'stores_low_stock': raw_data.get('stores_low_stock', 'false').lower() == 'true',
                'stores_low_stock_combined': raw_data.get('stores_low_stock_combined', 'false').lower() == 'true',
            }
            
            # Clean up empty values
            product = {k: v for k, v in product.items() if v is not None and v != ''}
            
            return product if product.get('lcbo_id') else None
            
        except Exception as e:
            logger.error(f"Error extracting product from result: {e}")
            return None
    
    def _safe_float(self, value) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def _parse_volume(self, volume_str: str) -> Optional[int]:
        if not volume_str:
            return None
        
        try:
            volume_str = str(volume_str).strip()
            
            if volume_str.isdigit():
                return int(volume_str)
            
            volume_str = volume_str.replace(',', '').replace(' ', '')
            
            if 'ml' in volume_str.lower():
                return int(float(volume_str.lower().replace('ml', '')))
            elif 'l' in volume_str.lower():
                return int(float(volume_str.lower().replace('l', '')) * 1000)
            
            return int(float(volume_str))
            
        except (ValueError, TypeError):
            logger.debug(f"Could not parse volume: {volume_str}")
            return None
    
    def parse_pagination_info(self, response_data: Dict) -> Dict:
        try:
            total_count = response_data.get('totalCount', 0)
            results_per_page = response_data.get('resultsPerPage', 20)
            duration = response_data.get('duration', 0)
            
            return {
                'total_count': total_count,
                'results_per_page': results_per_page,
                'total_pages': (total_count + results_per_page - 1) // results_per_page,
                'duration_ms': duration
            }
        except Exception as e:
            logger.error(f"Error parsing pagination info: {e}")
            return {
                'total_count': 0,
                'results_per_page': 20,
                'total_pages': 0,
                'duration_ms': 0
            }