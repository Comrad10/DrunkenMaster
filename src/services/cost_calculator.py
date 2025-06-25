import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from src.models import (
    Recipe, RecipeIngredient, DrinkCostCalculation, IngredientCost, 
    Product, StoreInventory, get_session
)
from src.services.product_matcher import ProductMatcher
from src.storage import StoreStorage
from src.utils import logger

class DrinkCostCalculator:
    """Service for calculating the cost of making drinks based on LCBO prices"""
    
    def __init__(self, city: str = "St. Catharines"):
        self.city = city
        self.product_matcher = ProductMatcher()
        self.store_storage = StoreStorage()
        
        # Cost assumptions for non-alcohol ingredients (per ml)
        self.mixer_costs = {
            'simple syrup': 0.002,       # $0.002/ml
            'lime juice': 0.02,          # $0.02/ml (fresh lime)
            'lemon juice': 0.02,         # $0.02/ml (fresh lemon)
            'orange juice': 0.005,       # $0.005/ml
            'cranberry juice': 0.004,    # $0.004/ml
            'club soda': 0.001,          # $0.001/ml
            'tonic water': 0.002,        # $0.002/ml
            'ginger beer': 0.003,        # $0.003/ml
            'grenadine': 0.01,           # $0.01/ml
            'angostura bitters': 0.20,   # $0.20/ml (expensive per ml, small amounts)
            'salt': 0.0001,              # $0.0001/ml
            'sugar': 0.001,              # $0.001/ml
        }
    
    def calculate_drink_cost(self, recipe_id: int, cost_options: str = 'mid_range') -> Optional[DrinkCostCalculation]:
        """Calculate the cost of making a drink"""
        with get_session() as session:
            recipe = session.query(Recipe).filter_by(id=recipe_id).first()
            if not recipe:
                logger.error(f"Recipe with ID {recipe_id} not found")
                return None
            
            logger.info(f"Calculating cost for recipe: {recipe.name}")
            
            # Get all ingredients
            ingredients = session.query(RecipeIngredient).filter_by(recipe_id=recipe_id).all()
            if not ingredients:
                logger.error(f"No ingredients found for recipe {recipe.name}")
                return None
            
            # Create cost calculation record
            calculation = DrinkCostCalculation(
                recipe_id=recipe_id,
                total_alcohol_cost=0.0,
                total_mixer_cost=0.0,
                total_cost=0.0,
                calculation_date=datetime.utcnow(),
                city=self.city,
                all_ingredients_available=True,
                missing_ingredients="[]",
                ingredients_on_sale="[]",
                total_sale_savings=0.0
            )
            
            ingredient_costs = []
            missing_ingredients = []
            sale_ingredients = []
            total_sale_savings = 0.0
            
            for ingredient in ingredients:
                logger.info(f"Processing ingredient: {ingredient.ingredient_name}")
                
                if ingredient.ingredient_type == 'alcohol':
                    # Find matching LCBO products
                    cost_data = self._calculate_alcohol_cost(ingredient, cost_options)
                    if cost_data:
                        ingredient_costs.append(cost_data)
                        calculation.total_alcohol_cost += cost_data['ingredient_cost']
                        
                        # Check for sales
                        if cost_data['is_on_sale']:
                            sale_ingredients.append({
                                'ingredient': ingredient.ingredient_name,
                                'product': cost_data['product_name'],
                                'savings': cost_data['sale_savings']
                            })
                            total_sale_savings += cost_data['sale_savings']
                    else:
                        missing_ingredients.append(ingredient.ingredient_name)
                        calculation.all_ingredients_available = False
                        
                else:
                    # Calculate mixer/garnish costs
                    mixer_cost = self._calculate_mixer_cost(ingredient)
                    if mixer_cost:
                        ingredient_costs.append(mixer_cost)
                        calculation.total_mixer_cost += mixer_cost['ingredient_cost']
            
            # Update calculation totals
            calculation.total_cost = calculation.total_alcohol_cost + calculation.total_mixer_cost
            calculation.cost_per_ml = calculation.total_cost / recipe.serving_size_ml if recipe.serving_size_ml else 0
            
            # Set markup suggestions (typical bar markups)
            calculation.markup_suggested = 300.0  # 300% markup is common for cocktails
            calculation.suggested_selling_price = calculation.total_cost * (1 + calculation.markup_suggested / 100)
            
            # Store missing ingredients and sale info
            calculation.missing_ingredients = json.dumps(missing_ingredients)
            calculation.ingredients_on_sale = json.dumps(sale_ingredients)
            calculation.total_sale_savings = total_sale_savings
            
            # Calculate price range options
            calculation.lowest_cost_option = self._calculate_option_cost(recipe_id, 'cheapest')
            calculation.premium_cost_option = self._calculate_option_cost(recipe_id, 'premium')
            
            # Save calculation
            session.add(calculation)
            session.flush()
            
            # Save individual ingredient costs
            for cost_data in ingredient_costs:
                cost_data['calculation_id'] = calculation.id
                ingredient_cost = IngredientCost(**cost_data)
                session.add(ingredient_cost)
            
            session.commit()
            logger.info(f"Cost calculation completed for {recipe.name}: ${calculation.total_cost:.3f}")
            
            # Detach from session
            session.expunge(calculation)
            return calculation
    
    def _calculate_alcohol_cost(self, ingredient: RecipeIngredient, cost_option: str = 'mid_range') -> Optional[Dict]:
        """Calculate cost for an alcohol ingredient"""
        try:
            # Find matching products
            if cost_option == 'best_match':
                product = self.product_matcher.find_best_match(ingredient)
                products = {'best': product} if product else {}
            else:
                products = self.product_matcher.find_price_range_options(ingredient)
            
            if not products or not products.get(cost_option):
                logger.warning(f"No {cost_option} product found for {ingredient.ingredient_name}")
                return None
            
            product = products[cost_option]
            
            # Check if product is in stock
            in_stock, stores_available = self._check_product_availability(product.lcbo_id)
            
            # Calculate costs
            if not product.price or not product.volume_ml:
                logger.warning(f"Missing price or volume data for product {product.lcbo_id}")
                return None
            
            price_per_ml = product.price / product.volume_ml
            amount_needed_ml = ingredient.amount_ml or 0
            ingredient_cost = price_per_ml * amount_needed_ml
            
            # Check for sales
            is_on_sale = product.regular_price and product.regular_price > product.price
            sale_savings = 0.0
            if is_on_sale:
                regular_price_per_ml = product.regular_price / product.volume_ml
                sale_savings = (regular_price_per_ml - price_per_ml) * amount_needed_ml
            
            return {
                'recipe_ingredient_id': ingredient.id,
                'lcbo_product_id': product.lcbo_id,
                'product_name': product.name,
                'brand': product.brand,
                'product_price': product.price,
                'product_volume_ml': product.volume_ml,
                'price_per_ml': price_per_ml,
                'regular_price': product.regular_price,
                'is_on_sale': is_on_sale,
                'sale_savings': sale_savings,
                'amount_needed_ml': amount_needed_ml,
                'ingredient_cost': ingredient_cost,
                'in_stock': in_stock,
                'stores_available': json.dumps(stores_available),
                'is_cheapest_option': cost_option == 'cheapest',
                'is_premium_option': cost_option == 'premium',
                'alternative_rank': 1
            }
            
        except Exception as e:
            logger.error(f"Error calculating alcohol cost for {ingredient.ingredient_name}: {e}")
            return None
    
    def _calculate_mixer_cost(self, ingredient: RecipeIngredient) -> Optional[Dict]:
        """Calculate cost for a non-alcohol ingredient"""
        try:
            ingredient_name_lower = ingredient.ingredient_name.lower()
            
            # Find cost per ml in our mixer cost database
            cost_per_ml = None
            for mixer_name, cost in self.mixer_costs.items():
                if mixer_name in ingredient_name_lower:
                    cost_per_ml = cost
                    break
            
            # Default cost for unknown mixers
            if cost_per_ml is None:
                if 'juice' in ingredient_name_lower:
                    cost_per_ml = 0.01  # Default juice cost
                elif 'syrup' in ingredient_name_lower:
                    cost_per_ml = 0.005  # Default syrup cost
                elif 'bitters' in ingredient_name_lower:
                    cost_per_ml = 0.15  # Default bitters cost
                else:
                    cost_per_ml = 0.005  # Generic mixer cost
            
            amount_needed_ml = ingredient.amount_ml or 0
            ingredient_cost = cost_per_ml * amount_needed_ml
            
            return {
                'recipe_ingredient_id': ingredient.id,
                'lcbo_product_id': 'MIXER',
                'product_name': ingredient.ingredient_name,
                'brand': 'Generic',
                'product_price': cost_per_ml * 1000,  # Price per liter
                'product_volume_ml': 1000.0,
                'price_per_ml': cost_per_ml,
                'regular_price': None,
                'is_on_sale': False,
                'sale_savings': 0.0,
                'amount_needed_ml': amount_needed_ml,
                'ingredient_cost': ingredient_cost,
                'in_stock': True,  # Assume mixers are always available
                'stores_available': json.dumps(['grocery_store']),
                'is_cheapest_option': True,
                'is_premium_option': False,
                'alternative_rank': 1
            }
            
        except Exception as e:
            logger.error(f"Error calculating mixer cost for {ingredient.ingredient_name}: {e}")
            return None
    
    def _check_product_availability(self, lcbo_id: str) -> Tuple[bool, List[str]]:
        """Check if product is available in stores"""
        try:
            availability = self.store_storage.get_product_availability(lcbo_id, self.city)
            
            in_stock = any(item['in_stock'] for item in availability)
            stores_available = [item['store_name'] for item in availability if item['in_stock']]
            
            return in_stock, stores_available
            
        except Exception as e:
            logger.debug(f"Error checking availability for {lcbo_id}: {e}")
            return False, []
    
    def _calculate_option_cost(self, recipe_id: int, cost_option: str) -> float:
        """Calculate total cost for a specific cost option (cheapest/premium)"""
        with get_session() as session:
            ingredients = session.query(RecipeIngredient).filter_by(recipe_id=recipe_id).all()
            total_cost = 0.0
            
            for ingredient in ingredients:
                if ingredient.ingredient_type == 'alcohol':
                    cost_data = self._calculate_alcohol_cost(ingredient, cost_option)
                    if cost_data:
                        total_cost += cost_data['ingredient_cost']
                else:
                    mixer_cost = self._calculate_mixer_cost(ingredient)
                    if mixer_cost:
                        total_cost += mixer_cost['ingredient_cost']
            
            return total_cost
    
    def get_cost_breakdown(self, calculation_id: int) -> Dict:
        """Get detailed cost breakdown for a calculation"""
        with get_session() as session:
            calculation = session.query(DrinkCostCalculation).filter_by(id=calculation_id).first()
            if not calculation:
                return {}
            
            ingredient_costs = session.query(IngredientCost).filter_by(calculation_id=calculation_id).all()
            
            breakdown = {
                'recipe_name': calculation.recipe.name,
                'total_cost': calculation.total_cost,
                'cost_per_ml': calculation.cost_per_ml,
                'suggested_price': calculation.suggested_selling_price,
                'markup_percentage': calculation.markup_suggested,
                'ingredients': [],
                'availability': {
                    'all_available': calculation.all_ingredients_available,
                    'missing': json.loads(calculation.missing_ingredients),
                    'on_sale': json.loads(calculation.ingredients_on_sale),
                    'total_savings': calculation.total_sale_savings
                },
                'cost_options': {
                    'cheapest': calculation.lowest_cost_option,
                    'current': calculation.total_cost,
                    'premium': calculation.premium_cost_option
                }
            }
            
            for cost in ingredient_costs:
                breakdown['ingredients'].append({
                    'name': cost.product_name,
                    'brand': cost.brand,
                    'amount_needed': f"{cost.amount_needed_ml:.1f}ml",
                    'cost': f"${cost.ingredient_cost:.3f}",
                    'price_per_ml': f"${cost.price_per_ml:.4f}",
                    'bottle_price': f"${cost.product_price:.2f}" if cost.product_price else "N/A",
                    'bottle_size': f"{cost.product_volume_ml:.0f}ml" if cost.product_volume_ml else "N/A",
                    'in_stock': cost.in_stock,
                    'on_sale': cost.is_on_sale,
                    'sale_savings': f"${cost.sale_savings:.3f}" if cost.sale_savings > 0 else None
                })
            
            return breakdown
    
    def compare_recipes(self, recipe_ids: List[int]) -> List[Dict]:
        """Compare costs across multiple recipes"""
        comparisons = []
        
        for recipe_id in recipe_ids:
            calculation = self.calculate_drink_cost(recipe_id)
            if calculation:
                comparisons.append({
                    'recipe_id': recipe_id,
                    'recipe_name': calculation.recipe.name,
                    'total_cost': calculation.total_cost,
                    'cost_per_ml': calculation.cost_per_ml,
                    'suggested_price': calculation.suggested_selling_price,
                    'profit_margin': calculation.suggested_selling_price - calculation.total_cost,
                    'all_available': calculation.all_ingredients_available
                })
        
        # Sort by cost
        comparisons.sort(key=lambda x: x['total_cost'])
        
        return comparisons