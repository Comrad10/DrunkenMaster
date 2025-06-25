from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from src.models import RecipeIngredient, get_session
from src.utils import logger

class IngredientService:
    """Service for managing recipe ingredients"""
    
    def __init__(self):
        pass
    
    def add_ingredient_to_recipe(self, recipe_id: int, ingredient_data: Dict) -> Optional[RecipeIngredient]:
        """Add a new ingredient to an existing recipe"""
        with get_session() as session:
            try:
                # Convert amount to ml if needed
                amount_ml = self._convert_to_ml(
                    ingredient_data['amount'], 
                    ingredient_data['unit']
                )
                
                ingredient = RecipeIngredient(
                    recipe_id=recipe_id,
                    ingredient_name=ingredient_data['ingredient_name'],
                    ingredient_type=ingredient_data.get('ingredient_type', 'alcohol'),
                    amount=ingredient_data['amount'],
                    unit=ingredient_data['unit'],
                    amount_ml=amount_ml,
                    alcohol_category=ingredient_data.get('alcohol_category'),
                    alcohol_subcategory=ingredient_data.get('alcohol_subcategory'),
                    min_alcohol_percentage=ingredient_data.get('min_alcohol_percentage'),
                    brand_preference=ingredient_data.get('brand_preference'),
                    notes=ingredient_data.get('notes'),
                    is_essential=ingredient_data.get('is_essential', True)
                )
                
                session.add(ingredient)
                session.commit()
                session.refresh(ingredient)  # Refresh to get the ID
                session.expunge(ingredient)  # Detach from session
                logger.info(f"Added ingredient {ingredient_data['ingredient_name']} to recipe {recipe_id}")
                return ingredient
                
            except Exception as e:
                logger.error(f"Error adding ingredient to recipe {recipe_id}: {e}")
                session.rollback()
                return None
    
    def update_ingredient(self, ingredient_id: int, updates: Dict) -> bool:
        """Update an existing ingredient"""
        with get_session() as session:
            try:
                ingredient = session.query(RecipeIngredient).filter_by(id=ingredient_id).first()
                if not ingredient:
                    return False
                
                # Update fields
                for field, value in updates.items():
                    if hasattr(ingredient, field):
                        setattr(ingredient, field, value)
                
                # Recalculate amount_ml if amount or unit changed
                if 'amount' in updates or 'unit' in updates:
                    ingredient.amount_ml = self._convert_to_ml(ingredient.amount, ingredient.unit)
                
                session.commit()
                ingredient_name = ingredient.ingredient_name  # Get name before expunge
                session.expunge(ingredient)  # Detach from session
                logger.info(f"Updated ingredient {ingredient_name}")
                return True
                
            except Exception as e:
                logger.error(f"Error updating ingredient {ingredient_id}: {e}")
                session.rollback()
                return False
    
    def remove_ingredient(self, ingredient_id: int) -> bool:
        """Remove an ingredient from a recipe"""
        with get_session() as session:
            try:
                ingredient = session.query(RecipeIngredient).filter_by(id=ingredient_id).first()
                if not ingredient:
                    return False
                
                ingredient_name = ingredient.ingredient_name
                session.delete(ingredient)
                session.commit()
                logger.info(f"Removed ingredient {ingredient_name}")
                return True
                
            except Exception as e:
                logger.error(f"Error removing ingredient {ingredient_id}: {e}")
                session.rollback()
                return False
    
    def get_ingredient_by_id(self, ingredient_id: int) -> Optional[RecipeIngredient]:
        """Get an ingredient by ID"""
        with get_session() as session:
            ingredient = session.query(RecipeIngredient).filter_by(id=ingredient_id).first()
            if ingredient:
                session.expunge(ingredient)
            return ingredient
    
    def _convert_to_ml(self, amount: float, unit: str) -> float:
        """Convert various units to milliliters"""
        unit_lower = unit.lower()
        
        conversion_table = {
            'ml': 1.0,
            'milliliter': 1.0,
            'milliliters': 1.0,
            'oz': 29.5735,  # US fluid ounce
            'ounce': 29.5735,
            'ounces': 29.5735,
            'fl oz': 29.5735,
            'tbsp': 14.7868,  # tablespoon
            'tablespoon': 14.7868,
            'tsp': 4.92892,  # teaspoon
            'teaspoon': 4.92892,
            'dash': 0.625,  # approximately 1/8 teaspoon
            'splash': 5.0,  # approximately 1 teaspoon
            'drop': 0.05,
            'cl': 10.0,  # centiliter
            'dl': 100.0,  # deciliter
            'l': 1000.0,  # liter
            'cup': 236.588,  # US cup
            'pint': 473.176,  # US pint
            'shot': 44.3603,  # US shot (1.5 oz)
            'jigger': 44.3603,  # same as shot
            'pony': 22.1802,  # 0.75 oz
            'whole': 1.0,  # for eggs, etc.
            'leaves': 0.1,  # estimate for mint leaves
            'pinch': 0.5,  # estimate for salt/spices
        }
        
        if unit_lower in conversion_table:
            return amount * conversion_table[unit_lower]
        else:
            logger.warning(f"Unknown unit '{unit}', assuming ml")
            return amount