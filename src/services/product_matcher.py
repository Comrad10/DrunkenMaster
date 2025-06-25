import re
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from src.models import Product, RecipeIngredient, get_session
from src.utils import logger

class ProductMatcher:
    """Service for matching recipe ingredients to LCBO products"""
    
    def __init__(self):
        # Common alcohol type mappings
        self.alcohol_mappings = {
            'vodka': {'categories': ['Spirits'], 'subcategories': ['Vodka'], 'keywords': ['vodka']},
            'gin': {'categories': ['Spirits'], 'subcategories': ['Gin'], 'keywords': ['gin', 'london dry', 'plymouth']},
            'rum': {'categories': ['Spirits'], 'subcategories': ['Rum'], 'keywords': ['rum', 'white rum', 'dark rum', 'spiced rum']},
            'whiskey': {'categories': ['Spirits'], 'subcategories': ['Whisky', 'Whiskey'], 'keywords': ['whiskey', 'whisky', 'bourbon', 'rye', 'scotch']},
            'whisky': {'categories': ['Spirits'], 'subcategories': ['Whisky', 'Whiskey'], 'keywords': ['whiskey', 'whisky', 'bourbon', 'rye', 'scotch']},
            'bourbon': {'categories': ['Spirits'], 'subcategories': ['Whisky', 'Whiskey'], 'keywords': ['bourbon', 'whiskey']},
            'scotch': {'categories': ['Spirits'], 'subcategories': ['Whisky', 'Whiskey'], 'keywords': ['scotch', 'whisky']},
            'tequila': {'categories': ['Spirits'], 'subcategories': ['Tequila'], 'keywords': ['tequila', 'silver tequila', 'gold tequila']},
            'brandy': {'categories': ['Spirits'], 'subcategories': ['Brandy'], 'keywords': ['brandy', 'cognac']},
            'triple sec': {'categories': ['Spirits'], 'subcategories': ['Liqueur'], 'keywords': ['triple sec', 'orange liqueur', 'cointreau', 'grand marnier']},
            'vermouth': {'categories': ['Wine'], 'subcategories': ['Vermouth'], 'keywords': ['vermouth', 'dry vermouth', 'sweet vermouth']},
            'amaretto': {'categories': ['Spirits'], 'subcategories': ['Liqueur'], 'keywords': ['amaretto', 'almond liqueur']},
            'kahlua': {'categories': ['Spirits'], 'subcategories': ['Liqueur'], 'keywords': ['kahlua', 'coffee liqueur']},
            'baileys': {'categories': ['Spirits'], 'subcategories': ['Liqueur'], 'keywords': ['baileys', 'irish cream']},
            'wine': {'categories': ['Wine'], 'subcategories': ['Red Wine', 'White Wine'], 'keywords': ['wine', 'red wine', 'white wine']},
            'beer': {'categories': ['Beer & Cider'], 'subcategories': ['Beer'], 'keywords': ['beer', 'lager', 'ale']},
            'champagne': {'categories': ['Wine'], 'subcategories': ['Sparkling Wine'], 'keywords': ['champagne', 'sparkling wine', 'prosecco']},
        }
        
        # Common brand mappings
        self.brand_keywords = {
            'grey goose': 'Grey Goose',
            'absolut': 'Absolut',
            'smirnoff': 'Smirnoff',
            'tanqueray': 'Tanqueray',
            'bombay': 'Bombay',
            'hendricks': "Hendrick's",
            'jack daniels': "Jack Daniel's",
            'jim beam': 'Jim Beam',
            'jameson': 'Jameson',
            'crown royal': 'Crown Royal',
            'johnnie walker': 'Johnnie Walker',
            'macallan': 'The Macallan',
            'patron': 'Patrón',
            'jose cuervo': 'Jose Cuervo',
            'bacardi': 'Bacardi',
            'captain morgan': 'Captain Morgan',
            'hennessy': 'Hennessy',
            'cointreau': 'Cointreau',
            'grand marnier': 'Grand Marnier',
        }
    
    def find_matching_products(self, ingredient: RecipeIngredient, limit: int = 10) -> List[Tuple[Product, float]]:
        """Find LCBO products that match a recipe ingredient"""
        with get_session() as session:
            # Start with base query for active products
            query = session.query(Product).filter_by(is_active=True)
            
            # Apply category filters
            category_filters = self._get_category_filters(ingredient)
            if category_filters:
                query = query.filter(Product.category.in_(category_filters))
            
            # Get initial candidates
            candidates = query.all()
            
            # Score and rank candidates
            scored_candidates = []
            for product in candidates:
                # Detach from session
                session.expunge(product)
                score = self._calculate_match_score(ingredient, product)
                if score > 0:
                    scored_candidates.append((product, score))
            
            # Sort by score (highest first) and return top matches
            scored_candidates.sort(key=lambda x: x[1], reverse=True)
            return scored_candidates[:limit]
    
    def _get_category_filters(self, ingredient: RecipeIngredient) -> List[str]:
        """Get category filters based on ingredient type"""
        filters = []
        
        # Use explicit category if provided
        if ingredient.alcohol_category:
            filters.append(ingredient.alcohol_category)
        
        # Look up in alcohol mappings
        ingredient_lower = ingredient.ingredient_name.lower()
        for alcohol_type, mapping in self.alcohol_mappings.items():
            if alcohol_type in ingredient_lower:
                filters.extend(mapping['categories'])
                break
        
        return list(set(filters))  # Remove duplicates
    
    def _calculate_match_score(self, ingredient: RecipeIngredient, product: Product) -> float:
        """Calculate how well a product matches an ingredient"""
        score = 0.0
        ingredient_lower = ingredient.ingredient_name.lower()
        product_name_lower = product.name.lower() if product.name else ""
        product_brand_lower = product.brand.lower() if product.brand else ""
        
        # Exact name match (highest score)
        if ingredient_lower == product_name_lower:
            score += 100.0
        
        # Brand preference match
        if ingredient.brand_preference:
            brand_lower = ingredient.brand_preference.lower()
            if brand_lower in product_brand_lower or brand_lower in product_name_lower:
                score += 50.0
        
        # Alcohol type matching
        alcohol_type_score = self._score_alcohol_type_match(ingredient_lower, product_name_lower, product_brand_lower)
        score += alcohol_type_score
        
        # Category/subcategory matching
        if ingredient.alcohol_category and product.category:
            if ingredient.alcohol_category.lower() == product.category.lower():
                score += 20.0
        
        if ingredient.alcohol_subcategory and product.subcategory:
            if ingredient.alcohol_subcategory.lower() == product.subcategory.lower():
                score += 15.0
        
        # ABV matching
        if ingredient.min_alcohol_percentage and product.alcohol_percentage:
            if product.alcohol_percentage >= ingredient.min_alcohol_percentage:
                score += 10.0
            else:
                score -= 20.0  # Penalize if ABV is too low
        
        # Keyword matching in product name
        keyword_score = self._score_keyword_match(ingredient_lower, product_name_lower)
        score += keyword_score
        
        # Brand keyword matching
        brand_score = self._score_brand_match(ingredient_lower, product_brand_lower, product_name_lower)
        score += brand_score
        
        # Price preference (prefer mid-range products)
        if product.price:
            if 20 <= product.price <= 80:  # Sweet spot for bar inventory
                score += 5.0
            elif product.price > 150:  # Very expensive
                score -= 10.0
        
        # Volume preference (prefer standard bottle sizes)
        if product.volume_ml:
            if product.volume_ml in [375, 500, 750, 1000, 1140]:  # Standard sizes
                score += 3.0
        
        return max(0.0, score)
    
    def _score_alcohol_type_match(self, ingredient_name: str, product_name: str, product_brand: str) -> float:
        """Score based on alcohol type keywords"""
        score = 0.0
        
        for alcohol_type, mapping in self.alcohol_mappings.items():
            if alcohol_type in ingredient_name:
                for keyword in mapping['keywords']:
                    if keyword in product_name or keyword in product_brand:
                        score += 30.0
                        break
                break
        
        return score
    
    def _score_keyword_match(self, ingredient_name: str, product_name: str) -> float:
        """Score based on keyword matches"""
        score = 0.0
        
        # Split ingredient name into words
        ingredient_words = re.findall(r'\w+', ingredient_name.lower())
        
        for word in ingredient_words:
            if len(word) >= 3:  # Only consider words with 3+ characters
                if word in product_name:
                    score += 5.0
        
        return score
    
    def _score_brand_match(self, ingredient_name: str, product_brand: str, product_name: str) -> float:
        """Score based on brand keyword matches"""
        score = 0.0
        
        for brand_keyword, brand_name in self.brand_keywords.items():
            if brand_keyword in ingredient_name:
                if brand_name.lower() in product_brand or brand_name.lower() in product_name:
                    score += 40.0
                    break
        
        return score
    
    def find_best_match(self, ingredient: RecipeIngredient) -> Optional[Product]:
        """Find the best single match for an ingredient"""
        matches = self.find_matching_products(ingredient, limit=1)
        return matches[0][0] if matches else None
    
    def find_price_range_options(self, ingredient: RecipeIngredient) -> Dict[str, Optional[Product]]:
        """Find cheapest, mid-range, and premium options for an ingredient"""
        matches = self.find_matching_products(ingredient, limit=20)
        
        if not matches:
            return {'cheapest': None, 'mid_range': None, 'premium': None}
        
        # Sort by price per ml for fair comparison
        price_sorted = []
        for product, score in matches:
            if product.price and product.volume_ml:
                price_per_ml = product.price / product.volume_ml
                price_sorted.append((product, score, price_per_ml))
        
        if not price_sorted:
            return {'cheapest': None, 'mid_range': None, 'premium': None}
        
        price_sorted.sort(key=lambda x: x[2])  # Sort by price per ml
        
        result = {
            'cheapest': price_sorted[0][0],
            'mid_range': None,
            'premium': None
        }
        
        if len(price_sorted) >= 2:
            mid_index = len(price_sorted) // 2
            result['mid_range'] = price_sorted[mid_index][0]
        
        if len(price_sorted) >= 3:
            result['premium'] = price_sorted[-1][0]
        
        return result
    
    def search_products_by_name(self, search_term: str, category: str = None) -> List[Product]:
        """Search products by name with optional category filter"""
        with get_session() as session:
            query = session.query(Product).filter_by(is_active=True)
            
            # Add name search
            query = query.filter(Product.name.ilike(f"%{search_term}%"))
            
            # Add category filter if provided
            if category:
                query = query.filter(Product.category.ilike(f"%{category}%"))
            
            return query.limit(20).all()
    
    def get_products_by_category(self, category: str, subcategory: str = None) -> List[Product]:
        """Get products by category and optional subcategory"""
        with get_session() as session:
            query = session.query(Product).filter_by(is_active=True)
            query = query.filter(Product.category.ilike(f"%{category}%"))
            
            if subcategory:
                query = query.filter(Product.subcategory.ilike(f"%{subcategory}%"))
            
            return query.all()
    
    def verify_ingredient_match(self, ingredient: RecipeIngredient, product: Product) -> Dict[str, any]:
        """Verify and provide details about how well a product matches an ingredient"""
        score = self._calculate_match_score(ingredient, product)
        
        verification = {
            'overall_score': score,
            'match_quality': 'Poor' if score < 20 else 'Good' if score < 50 else 'Excellent',
            'checks': {
                'category_match': False,
                'abv_sufficient': False,
                'brand_match': False,
                'name_similarity': False
            },
            'issues': []
        }
        
        # Category check
        if ingredient.alcohol_category and product.category:
            verification['checks']['category_match'] = ingredient.alcohol_category.lower() in product.category.lower()
        
        # ABV check
        if ingredient.min_alcohol_percentage and product.alcohol_percentage:
            verification['checks']['abv_sufficient'] = product.alcohol_percentage >= ingredient.min_alcohol_percentage
            if not verification['checks']['abv_sufficient']:
                verification['issues'].append(f"ABV too low: {product.alcohol_percentage}% < {ingredient.min_alcohol_percentage}%")
        
        # Brand check
        if ingredient.brand_preference:
            brand_lower = ingredient.brand_preference.lower()
            product_brand_lower = product.brand.lower() if product.brand else ""
            product_name_lower = product.name.lower() if product.name else ""
            verification['checks']['brand_match'] = brand_lower in product_brand_lower or brand_lower in product_name_lower
        
        # Name similarity check
        ingredient_lower = ingredient.ingredient_name.lower()
        product_name_lower = product.name.lower() if product.name else ""
        verification['checks']['name_similarity'] = any(word in product_name_lower for word in ingredient_lower.split() if len(word) >= 3)
        
        return verification