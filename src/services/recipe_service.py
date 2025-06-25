import json
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from src.models import Recipe, RecipeIngredient, get_session
from src.utils import logger

class RecipeService:
    """Service for managing drink recipes and ingredients"""
    
    def __init__(self):
        pass
    
    def create_recipe(self, recipe_data: Dict) -> Optional[Recipe]:
        """Create a new recipe with ingredients"""
        with get_session() as session:
            try:
                recipe = Recipe(
                    name=recipe_data['name'],
                    category=recipe_data.get('category', 'Cocktail'),
                    description=recipe_data.get('description'),
                    instructions=recipe_data.get('instructions'),
                    garnish=recipe_data.get('garnish'),
                    glass_type=recipe_data.get('glass_type'),
                    difficulty=recipe_data.get('difficulty', 'Medium'),
                    prep_time_minutes=recipe_data.get('prep_time_minutes', 5),
                    serving_size_ml=recipe_data.get('serving_size_ml', 120.0),
                    source=recipe_data.get('source', 'Manual Entry')
                )
                
                session.add(recipe)
                session.flush()
                
                # Add ingredients
                for ingredient_data in recipe_data.get('ingredients', []):
                    ingredient = self._create_recipe_ingredient(recipe.id, ingredient_data)
                    session.add(ingredient)
                
                session.commit()
                logger.info(f"Created recipe: {recipe.name}")
                return recipe
                
            except Exception as e:
                logger.error(f"Error creating recipe: {e}")
                session.rollback()
                return None
    
    def _create_recipe_ingredient(self, recipe_id: int, ingredient_data: Dict) -> RecipeIngredient:
        """Create a recipe ingredient from data"""
        # Convert amount to ml if needed
        amount_ml = self._convert_to_ml(
            ingredient_data['amount'], 
            ingredient_data['unit']
        )
        
        return RecipeIngredient(
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
        }
        
        if unit_lower in conversion_table:
            return amount * conversion_table[unit_lower]
        else:
            logger.warning(f"Unknown unit '{unit}', assuming ml")
            return amount
    
    def find_recipe_by_name(self, name: str) -> Optional[Recipe]:
        """Find a recipe by name (case-insensitive)"""
        with get_session() as session:
            recipe = session.query(Recipe).filter(
                Recipe.name.ilike(f"%{name}%"),
                Recipe.is_active == True
            ).first()
            if recipe:
                session.expunge(recipe)
            return recipe
    
    def search_recipes(self, query: str) -> List[Recipe]:
        """Search recipes by name or category"""
        with get_session() as session:
            return session.query(Recipe).filter(
                Recipe.name.ilike(f"%{query}%") | 
                Recipe.category.ilike(f"%{query}%"),
                Recipe.is_active == True
            ).all()
    
    def get_recipe_ingredients(self, recipe_id: int) -> List[RecipeIngredient]:
        """Get all ingredients for a recipe"""
        with get_session() as session:
            ingredients = session.query(RecipeIngredient).filter_by(recipe_id=recipe_id).all()
            for ingredient in ingredients:
                session.expunge(ingredient)
            return ingredients
    
    def load_default_recipes(self) -> int:
        """Load the top 50 most popular bar cocktail recipes"""
        default_recipes = [
            {
                'name': 'Old Fashioned',
                'category': 'Cocktail',
                'description': 'Classic whiskey cocktail with sugar and bitters',
                'instructions': '1. Muddle sugar with bitters in glass\n2. Add whiskey and ice\n3. Stir well\n4. Garnish with orange peel',
                'garnish': 'Orange peel',
                'glass_type': 'Old Fashioned Glass',
                'difficulty': 'Easy',
                'prep_time_minutes': 3,
                'serving_size_ml': 100.0,
                'ingredients': [
                    {'ingredient_name': 'Bourbon Whiskey', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Whisky', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Simple Syrup', 'ingredient_type': 'mixer', 'amount': 10, 'unit': 'ml'},
                    {'ingredient_name': 'Angostura Bitters', 'ingredient_type': 'mixer', 'amount': 2, 'unit': 'dash'},
                ]
            },
            {
                'name': 'Margarita',
                'category': 'Cocktail', 
                'description': 'Classic tequila cocktail with lime and triple sec',
                'instructions': '1. Rim glass with salt\n2. Shake all ingredients with ice\n3. Strain into glass over ice\n4. Garnish with lime wheel',
                'garnish': 'Lime wheel, salt rim',
                'glass_type': 'Margarita Glass',
                'difficulty': 'Easy',
                'prep_time_minutes': 4,
                'serving_size_ml': 150.0,
                'ingredients': [
                    {'ingredient_name': 'Silver Tequila', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Tequila', 'min_alcohol_percentage': 38.0},
                    {'ingredient_name': 'Triple Sec', 'ingredient_type': 'alcohol', 'amount': 30, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                    {'ingredient_name': 'Fresh Lime Juice', 'ingredient_type': 'mixer', 'amount': 30, 'unit': 'ml'},
                ]
            },
            {
                'name': 'Martini',
                'category': 'Cocktail',
                'description': 'Classic gin and vermouth cocktail',
                'instructions': '1. Stir gin and vermouth with ice\n2. Strain into chilled glass\n3. Garnish with olive or lemon twist',
                'garnish': 'Olive or lemon twist',
                'glass_type': 'Martini Glass',
                'difficulty': 'Medium',
                'prep_time_minutes': 3,
                'serving_size_ml': 90.0,
                'ingredients': [
                    {'ingredient_name': 'London Dry Gin', 'ingredient_type': 'alcohol', 'amount': 75, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Gin', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Dry Vermouth', 'ingredient_type': 'alcohol', 'amount': 15, 'unit': 'ml', 'alcohol_category': 'Wine', 'alcohol_subcategory': 'Vermouth'},
                ]
            },
            {
                'name': 'Moscow Mule',
                'category': 'Cocktail',
                'description': 'Vodka cocktail with ginger beer and lime',
                'instructions': '1. Add vodka and lime juice to copper mug\n2. Fill with ice\n3. Top with ginger beer\n4. Stir gently\n5. Garnish with lime wheel',
                'garnish': 'Lime wheel',
                'glass_type': 'Copper Mug',
                'difficulty': 'Easy',
                'prep_time_minutes': 2,
                'serving_size_ml': 240.0,
                'ingredients': [
                    {'ingredient_name': 'Vodka', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Vodka', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Fresh Lime Juice', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                    {'ingredient_name': 'Ginger Beer', 'ingredient_type': 'mixer', 'amount': 180, 'unit': 'ml'},
                ]
            },
            {
                'name': 'Whiskey Sour',
                'category': 'Cocktail',
                'description': 'Whiskey cocktail with lemon juice and simple syrup',
                'instructions': '1. Shake whiskey, lemon juice, and simple syrup with ice\n2. Strain into glass over ice\n3. Garnish with cherry and orange slice',
                'garnish': 'Maraschino cherry, orange slice',
                'glass_type': 'Old Fashioned Glass',
                'difficulty': 'Easy',
                'prep_time_minutes': 3,
                'serving_size_ml': 120.0,
                'ingredients': [
                    {'ingredient_name': 'Bourbon Whiskey', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Whisky', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Fresh Lemon Juice', 'ingredient_type': 'mixer', 'amount': 30, 'unit': 'ml'},
                    {'ingredient_name': 'Simple Syrup', 'ingredient_type': 'mixer', 'amount': 20, 'unit': 'ml'},
                ]
            },
            # Additional popular cocktails
            {
                'name': 'Cosmopolitan',
                'category': 'Cocktail',
                'description': 'Vodka cocktail with cranberry juice and lime',
                'instructions': '1. Shake vodka, triple sec, cranberry juice, and lime juice with ice\n2. Strain into chilled martini glass\n3. Garnish with lime wheel',
                'garnish': 'Lime wheel',
                'glass_type': 'Martini Glass',
                'difficulty': 'Easy',
                'prep_time_minutes': 3,
                'serving_size_ml': 100.0,
                'ingredients': [
                    {'ingredient_name': 'Vodka', 'ingredient_type': 'alcohol', 'amount': 45, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Vodka', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Triple Sec', 'ingredient_type': 'alcohol', 'amount': 15, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                    {'ingredient_name': 'Cranberry Juice', 'ingredient_type': 'mixer', 'amount': 30, 'unit': 'ml'},
                    {'ingredient_name': 'Fresh Lime Juice', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                ]
            },
            {
                'name': 'Negroni',
                'category': 'Cocktail',
                'description': 'Italian aperitif with gin, vermouth, and Campari',
                'instructions': '1. Add all ingredients to old fashioned glass with ice\n2. Stir well\n3. Garnish with orange peel',
                'garnish': 'Orange peel',
                'glass_type': 'Old Fashioned Glass',
                'difficulty': 'Easy',
                'prep_time_minutes': 2,
                'serving_size_ml': 90.0,
                'ingredients': [
                    {'ingredient_name': 'London Dry Gin', 'ingredient_type': 'alcohol', 'amount': 30, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Gin', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Sweet Vermouth', 'ingredient_type': 'alcohol', 'amount': 30, 'unit': 'ml', 'alcohol_category': 'Wine', 'alcohol_subcategory': 'Vermouth'},
                    {'ingredient_name': 'Campari', 'ingredient_type': 'alcohol', 'amount': 30, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                ]
            },
            {
                'name': 'Manhattan',
                'category': 'Cocktail',
                'description': 'Classic whiskey cocktail with sweet vermouth',
                'instructions': '1. Stir whiskey and vermouth with ice\n2. Strain into chilled coupe\n3. Garnish with cherry',
                'garnish': 'Maraschino cherry',
                'glass_type': 'Coupe Glass',
                'difficulty': 'Medium',
                'prep_time_minutes': 3,
                'serving_size_ml': 75.0,
                'ingredients': [
                    {'ingredient_name': 'Rye Whiskey', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Whisky', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Sweet Vermouth', 'ingredient_type': 'alcohol', 'amount': 30, 'unit': 'ml', 'alcohol_category': 'Wine', 'alcohol_subcategory': 'Vermouth'},
                    {'ingredient_name': 'Angostura Bitters', 'ingredient_type': 'mixer', 'amount': 2, 'unit': 'dash'},
                ]
            },
            {
                'name': 'Daiquiri',
                'category': 'Cocktail',
                'description': 'Classic rum cocktail with lime juice and simple syrup',
                'instructions': '1. Shake rum, lime juice, and simple syrup with ice\n2. Strain into chilled coupe\n3. Garnish with lime wheel',
                'garnish': 'Lime wheel',
                'glass_type': 'Coupe Glass',
                'difficulty': 'Easy',
                'prep_time_minutes': 3,
                'serving_size_ml': 75.0,
                'ingredients': [
                    {'ingredient_name': 'White Rum', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Rum', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Fresh Lime Juice', 'ingredient_type': 'mixer', 'amount': 30, 'unit': 'ml'},
                    {'ingredient_name': 'Simple Syrup', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                ]
            },
            {
                'name': 'Piña Colada',
                'category': 'Cocktail',
                'description': 'Tropical rum cocktail with coconut cream and pineapple',
                'instructions': '1. Blend rum, coconut cream, pineapple juice, and ice\n2. Pour into hurricane glass\n3. Garnish with pineapple and cherry',
                'garnish': 'Pineapple wedge, cherry',
                'glass_type': 'Hurricane Glass',
                'difficulty': 'Easy',
                'prep_time_minutes': 3,
                'serving_size_ml': 240.0,
                'ingredients': [
                    {'ingredient_name': 'White Rum', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Rum', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Coconut Cream', 'ingredient_type': 'mixer', 'amount': 60, 'unit': 'ml'},
                    {'ingredient_name': 'Pineapple Juice', 'ingredient_type': 'mixer', 'amount': 120, 'unit': 'ml'},
                ]
            },
            {
                'name': 'Mojito',
                'category': 'Cocktail',
                'description': 'Cuban rum cocktail with mint, lime, and soda',
                'instructions': '1. Muddle mint leaves with lime juice\n2. Add rum and simple syrup\n3. Fill with ice and top with soda\n4. Garnish with mint sprig',
                'garnish': 'Fresh mint sprig',
                'glass_type': 'Highball Glass',
                'difficulty': 'Medium',
                'prep_time_minutes': 4,
                'serving_size_ml': 240.0,
                'ingredients': [
                    {'ingredient_name': 'White Rum', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Rum', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Fresh Lime Juice', 'ingredient_type': 'mixer', 'amount': 30, 'unit': 'ml'},
                    {'ingredient_name': 'Simple Syrup', 'ingredient_type': 'mixer', 'amount': 20, 'unit': 'ml'},
                    {'ingredient_name': 'Club Soda', 'ingredient_type': 'mixer', 'amount': 120, 'unit': 'ml'},
                    {'ingredient_name': 'Fresh Mint Leaves', 'ingredient_type': 'garnish', 'amount': 8, 'unit': 'leaves'},
                ]
            },
            {
                'name': 'Long Island Iced Tea',
                'category': 'Cocktail',
                'description': 'Strong mixed drink with multiple spirits',
                'instructions': '1. Add all spirits and lemon juice to glass with ice\n2. Top with cola\n3. Garnish with lemon wedge',
                'garnish': 'Lemon wedge',
                'glass_type': 'Highball Glass',
                'difficulty': 'Medium',
                'prep_time_minutes': 3,
                'serving_size_ml': 240.0,
                'ingredients': [
                    {'ingredient_name': 'Vodka', 'ingredient_type': 'alcohol', 'amount': 15, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Vodka', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'White Rum', 'ingredient_type': 'alcohol', 'amount': 15, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Rum', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'London Dry Gin', 'ingredient_type': 'alcohol', 'amount': 15, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Gin', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Silver Tequila', 'ingredient_type': 'alcohol', 'amount': 15, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Tequila', 'min_alcohol_percentage': 38.0},
                    {'ingredient_name': 'Triple Sec', 'ingredient_type': 'alcohol', 'amount': 15, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                    {'ingredient_name': 'Fresh Lemon Juice', 'ingredient_type': 'mixer', 'amount': 30, 'unit': 'ml'},
                    {'ingredient_name': 'Cola', 'ingredient_type': 'mixer', 'amount': 120, 'unit': 'ml'},
                ]
            },
            {
                'name': 'Mai Tai',
                'category': 'Cocktail',
                'description': 'Polynesian rum cocktail with orange liqueur and orgeat',
                'instructions': '1. Shake light rum, orange liqueur, orgeat, and lime juice with ice\n2. Pour into glass over ice\n3. Float dark rum on top\n4. Garnish with pineapple and cherry',
                'garnish': 'Pineapple wedge, cherry',
                'glass_type': 'Old Fashioned Glass',
                'difficulty': 'Medium',
                'prep_time_minutes': 4,
                'serving_size_ml': 150.0,
                'ingredients': [
                    {'ingredient_name': 'White Rum', 'ingredient_type': 'alcohol', 'amount': 30, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Rum', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Dark Rum', 'ingredient_type': 'alcohol', 'amount': 30, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Rum', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Orange Liqueur', 'ingredient_type': 'alcohol', 'amount': 15, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                    {'ingredient_name': 'Orgeat Syrup', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                    {'ingredient_name': 'Fresh Lime Juice', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                ]
            },
            {
                'name': 'Bloody Mary',
                'category': 'Cocktail',
                'description': 'Savory vodka cocktail with tomato juice and spices',
                'instructions': '1. Add vodka and tomato juice to glass with ice\n2. Add seasonings and stir\n3. Garnish with celery stalk and olives',
                'garnish': 'Celery stalk, olives',
                'glass_type': 'Highball Glass',
                'difficulty': 'Easy',
                'prep_time_minutes': 3,
                'serving_size_ml': 240.0,
                'ingredients': [
                    {'ingredient_name': 'Vodka', 'ingredient_type': 'alcohol', 'amount': 45, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Vodka', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Tomato Juice', 'ingredient_type': 'mixer', 'amount': 180, 'unit': 'ml'},
                    {'ingredient_name': 'Worcestershire Sauce', 'ingredient_type': 'mixer', 'amount': 3, 'unit': 'dash'},
                    {'ingredient_name': 'Hot Sauce', 'ingredient_type': 'mixer', 'amount': 2, 'unit': 'dash'},
                    {'ingredient_name': 'Celery Salt', 'ingredient_type': 'mixer', 'amount': 1, 'unit': 'pinch'},
                ]
            },
            {
                'name': 'Gimlet',
                'category': 'Cocktail',
                'description': 'Classic gin cocktail with lime juice',
                'instructions': '1. Shake gin and lime juice with ice\n2. Strain into chilled coupe\n3. Garnish with lime wheel',
                'garnish': 'Lime wheel',
                'glass_type': 'Coupe Glass',
                'difficulty': 'Easy',
                'prep_time_minutes': 2,
                'serving_size_ml': 75.0,
                'ingredients': [
                    {'ingredient_name': 'London Dry Gin', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Gin', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Fresh Lime Juice', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                    {'ingredient_name': 'Simple Syrup', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                ]
            },
            {
                'name': 'Dark and Stormy',
                'category': 'Cocktail',
                'description': 'Rum cocktail with ginger beer and lime',
                'instructions': '1. Add rum to glass with ice\n2. Top with ginger beer\n3. Squeeze lime wedge and drop in',
                'garnish': 'Lime wedge',
                'glass_type': 'Highball Glass',
                'difficulty': 'Easy',
                'prep_time_minutes': 1,
                'serving_size_ml': 240.0,
                'ingredients': [
                    {'ingredient_name': 'Dark Rum', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Rum', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Ginger Beer', 'ingredient_type': 'mixer', 'amount': 180, 'unit': 'ml'},
                    {'ingredient_name': 'Fresh Lime Juice', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                ]
            },
            {
                'name': 'Sazerac',
                'category': 'Cocktail',
                'description': 'New Orleans whiskey cocktail with absinthe rinse',
                'instructions': '1. Rinse glass with absinthe\n2. Stir whiskey, simple syrup, and bitters with ice\n3. Strain into glass\n4. Garnish with lemon peel',
                'garnish': 'Lemon peel',
                'glass_type': 'Old Fashioned Glass',
                'difficulty': 'Hard',
                'prep_time_minutes': 5,
                'serving_size_ml': 75.0,
                'ingredients': [
                    {'ingredient_name': 'Rye Whiskey', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Whisky', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Absinthe', 'ingredient_type': 'alcohol', 'amount': 5, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                    {'ingredient_name': 'Simple Syrup', 'ingredient_type': 'mixer', 'amount': 10, 'unit': 'ml'},
                    {'ingredient_name': 'Peychauds Bitters', 'ingredient_type': 'mixer', 'amount': 2, 'unit': 'dash'},
                ]
            },
            {
                'name': 'Mint Julep',
                'category': 'Cocktail',
                'description': 'Kentucky bourbon cocktail with mint',
                'instructions': '1. Muddle mint with simple syrup\n2. Add bourbon and crushed ice\n3. Stir and top with more ice\n4. Garnish with mint sprig',
                'garnish': 'Fresh mint sprig',
                'glass_type': 'Julep Cup',
                'difficulty': 'Medium',
                'prep_time_minutes': 4,
                'serving_size_ml': 120.0,
                'ingredients': [
                    {'ingredient_name': 'Bourbon Whiskey', 'ingredient_type': 'alcohol', 'amount': 75, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Whisky', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Simple Syrup', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                    {'ingredient_name': 'Fresh Mint Leaves', 'ingredient_type': 'garnish', 'amount': 8, 'unit': 'leaves'},
                ]
            },
            {
                'name': 'Caipirinha',
                'category': 'Cocktail',
                'description': 'Brazilian cocktail with cachaça and lime',
                'instructions': '1. Muddle lime wedges with sugar in glass\n2. Add cachaça and ice\n3. Stir well',
                'garnish': 'Lime wedges',
                'glass_type': 'Old Fashioned Glass',
                'difficulty': 'Easy',
                'prep_time_minutes': 3,
                'serving_size_ml': 120.0,
                'ingredients': [
                    {'ingredient_name': 'Cachaça', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Rum', 'min_alcohol_percentage': 38.0},
                    {'ingredient_name': 'Fresh Lime', 'ingredient_type': 'mixer', 'amount': 30, 'unit': 'ml'},
                    {'ingredient_name': 'Sugar', 'ingredient_type': 'mixer', 'amount': 10, 'unit': 'ml'},
                ]
            },
            {
                'name': 'Aperol Spritz',
                'category': 'Cocktail',
                'description': 'Italian aperitif with Aperol, prosecco, and soda',
                'instructions': '1. Add Aperol to wine glass with ice\n2. Top with prosecco and soda\n3. Garnish with orange slice',
                'garnish': 'Orange slice',
                'glass_type': 'Wine Glass',
                'difficulty': 'Easy',
                'prep_time_minutes': 2,
                'serving_size_ml': 180.0,
                'ingredients': [
                    {'ingredient_name': 'Aperol', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                    {'ingredient_name': 'Prosecco', 'ingredient_type': 'alcohol', 'amount': 90, 'unit': 'ml', 'alcohol_category': 'Wine', 'alcohol_subcategory': 'Sparkling Wine'},
                    {'ingredient_name': 'Club Soda', 'ingredient_type': 'mixer', 'amount': 30, 'unit': 'ml'},
                ]
            },
            {
                'name': 'Espresso Martini',
                'category': 'Cocktail',
                'description': 'Vodka cocktail with coffee liqueur and espresso',
                'instructions': '1. Shake vodka, coffee liqueur, and espresso with ice\n2. Strain into chilled martini glass\n3. Garnish with coffee beans',
                'garnish': 'Coffee beans',
                'glass_type': 'Martini Glass',
                'difficulty': 'Medium',
                'prep_time_minutes': 3,
                'serving_size_ml': 90.0,
                'ingredients': [
                    {'ingredient_name': 'Vodka', 'ingredient_type': 'alcohol', 'amount': 50, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Vodka', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Coffee Liqueur', 'ingredient_type': 'alcohol', 'amount': 20, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                    {'ingredient_name': 'Fresh Espresso', 'ingredient_type': 'mixer', 'amount': 30, 'unit': 'ml'},
                    {'ingredient_name': 'Simple Syrup', 'ingredient_type': 'mixer', 'amount': 10, 'unit': 'ml'},
                ]
            },
            {
                'name': 'French 75',
                'category': 'Cocktail',
                'description': 'Gin cocktail with lemon juice and champagne',
                'instructions': '1. Shake gin and lemon juice with ice\n2. Strain into flute\n3. Top with champagne\n4. Garnish with lemon twist',
                'garnish': 'Lemon twist',
                'glass_type': 'Champagne Flute',
                'difficulty': 'Medium',
                'prep_time_minutes': 3,
                'serving_size_ml': 120.0,
                'ingredients': [
                    {'ingredient_name': 'London Dry Gin', 'ingredient_type': 'alcohol', 'amount': 30, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Gin', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Fresh Lemon Juice', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                    {'ingredient_name': 'Simple Syrup', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                    {'ingredient_name': 'Champagne', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Wine', 'alcohol_subcategory': 'Sparkling Wine'},
                ]
            },
            {
                'name': 'Ramos Gin Fizz',
                'category': 'Cocktail',
                'description': 'Creamy gin cocktail with egg white and cream',
                'instructions': '1. Dry shake all ingredients except soda\n2. Shake with ice for 12 minutes\n3. Strain into collins glass\n4. Top with soda water',
                'garnish': None,
                'glass_type': 'Collins Glass',
                'difficulty': 'Hard',
                'prep_time_minutes': 15,
                'serving_size_ml': 180.0,
                'ingredients': [
                    {'ingredient_name': 'London Dry Gin', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Gin', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Fresh Lemon Juice', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                    {'ingredient_name': 'Fresh Lime Juice', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                    {'ingredient_name': 'Simple Syrup', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                    {'ingredient_name': 'Heavy Cream', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                    {'ingredient_name': 'Egg White', 'ingredient_type': 'mixer', 'amount': 1, 'unit': 'whole'},
                    {'ingredient_name': 'Club Soda', 'ingredient_type': 'mixer', 'amount': 60, 'unit': 'ml'},
                ]
            },
            {
                'name': 'Amaretto Sour',
                'category': 'Cocktail',
                'description': 'Sweet almond liqueur cocktail with lemon juice',
                'instructions': '1. Shake amaretto and lemon juice with ice\n2. Strain into glass over ice\n3. Garnish with cherry and orange',
                'garnish': 'Cherry, orange slice',
                'glass_type': 'Old Fashioned Glass',
                'difficulty': 'Easy',
                'prep_time_minutes': 2,
                'serving_size_ml': 90.0,
                'ingredients': [
                    {'ingredient_name': 'Amaretto', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                    {'ingredient_name': 'Fresh Lemon Juice', 'ingredient_type': 'mixer', 'amount': 30, 'unit': 'ml'},
                    {'ingredient_name': 'Simple Syrup', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                ]
            },
            {
                'name': 'Aviation',
                'category': 'Cocktail',
                'description': 'Gin cocktail with maraschino liqueur and crème de violette',
                'instructions': '1. Shake all ingredients with ice\n2. Strain into chilled coupe\n3. Garnish with cherry',
                'garnish': 'Maraschino cherry',
                'glass_type': 'Coupe Glass',
                'difficulty': 'Hard',
                'prep_time_minutes': 3,
                'serving_size_ml': 75.0,
                'ingredients': [
                    {'ingredient_name': 'London Dry Gin', 'ingredient_type': 'alcohol', 'amount': 45, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Gin', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Maraschino Liqueur', 'ingredient_type': 'alcohol', 'amount': 15, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                    {'ingredient_name': 'Crème de Violette', 'ingredient_type': 'alcohol', 'amount': 7.5, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                    {'ingredient_name': 'Fresh Lemon Juice', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                ]
            },
            {
                'name': 'Bee\'s Knees',
                'category': 'Cocktail',
                'description': 'Gin cocktail with honey syrup and lemon juice',
                'instructions': '1. Shake gin, honey syrup, and lemon juice with ice\n2. Strain into chilled coupe\n3. Garnish with lemon twist',
                'garnish': 'Lemon twist',
                'glass_type': 'Coupe Glass',
                'difficulty': 'Easy',
                'prep_time_minutes': 3,
                'serving_size_ml': 75.0,
                'ingredients': [
                    {'ingredient_name': 'London Dry Gin', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Gin', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Honey Syrup', 'ingredient_type': 'mixer', 'amount': 22.5, 'unit': 'ml'},
                    {'ingredient_name': 'Fresh Lemon Juice', 'ingredient_type': 'mixer', 'amount': 22.5, 'unit': 'ml'},
                ]
            },
            {
                'name': 'Boulevardier',
                'category': 'Cocktail',
                'description': 'Whiskey variation of the Negroni',
                'instructions': '1. Stir whiskey, vermouth, and Campari with ice\n2. Strain into old fashioned glass over ice\n3. Garnish with orange peel',
                'garnish': 'Orange peel',
                'glass_type': 'Old Fashioned Glass',
                'difficulty': 'Medium',
                'prep_time_minutes': 3,
                'serving_size_ml': 90.0,
                'ingredients': [
                    {'ingredient_name': 'Bourbon Whiskey', 'ingredient_type': 'alcohol', 'amount': 45, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Whisky', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Sweet Vermouth', 'ingredient_type': 'alcohol', 'amount': 30, 'unit': 'ml', 'alcohol_category': 'Wine', 'alcohol_subcategory': 'Vermouth'},
                    {'ingredient_name': 'Campari', 'ingredient_type': 'alcohol', 'amount': 30, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                ]
            },
            {
                'name': 'Paper Plane',
                'category': 'Cocktail',
                'description': 'Modern whiskey cocktail with equal parts',
                'instructions': '1. Shake all ingredients with ice\n2. Strain into chilled coupe\n3. Garnish with lemon twist',
                'garnish': 'Lemon twist',
                'glass_type': 'Coupe Glass',
                'difficulty': 'Medium',
                'prep_time_minutes': 3,
                'serving_size_ml': 90.0,
                'ingredients': [
                    {'ingredient_name': 'Bourbon Whiskey', 'ingredient_type': 'alcohol', 'amount': 22.5, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Whisky', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Aperol', 'ingredient_type': 'alcohol', 'amount': 22.5, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                    {'ingredient_name': 'Amaro Nonino', 'ingredient_type': 'alcohol', 'amount': 22.5, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                    {'ingredient_name': 'Fresh Lemon Juice', 'ingredient_type': 'mixer', 'amount': 22.5, 'unit': 'ml'},
                ]
            },
            {
                'name': 'Corpse Reviver #2',
                'category': 'Cocktail',
                'description': 'Classic gin cocktail with absinthe rinse',
                'instructions': '1. Rinse glass with absinthe\n2. Shake gin, cointreau, lillet, and lemon juice with ice\n3. Strain into glass\n4. Garnish with orange peel',
                'garnish': 'Orange peel',
                'glass_type': 'Coupe Glass',
                'difficulty': 'Hard',
                'prep_time_minutes': 4,
                'serving_size_ml': 75.0,
                'ingredients': [
                    {'ingredient_name': 'London Dry Gin', 'ingredient_type': 'alcohol', 'amount': 22.5, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Gin', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Cointreau', 'ingredient_type': 'alcohol', 'amount': 22.5, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                    {'ingredient_name': 'Lillet Blanc', 'ingredient_type': 'alcohol', 'amount': 22.5, 'unit': 'ml', 'alcohol_category': 'Wine', 'alcohol_subcategory': 'Vermouth'},
                    {'ingredient_name': 'Fresh Lemon Juice', 'ingredient_type': 'mixer', 'amount': 22.5, 'unit': 'ml'},
                    {'ingredient_name': 'Absinthe', 'ingredient_type': 'alcohol', 'amount': 2, 'unit': 'dash', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                ]
            },
            {
                'name': 'Penicillin',
                'category': 'Cocktail',
                'description': 'Modern scotch cocktail with honey, lemon, and ginger',
                'instructions': '1. Shake scotch, lemon juice, honey syrup, and ginger liqueur with ice\n2. Strain into glass over ice\n3. Float smoky scotch on top\n4. Garnish with candied ginger',
                'garnish': 'Candied ginger',
                'glass_type': 'Old Fashioned Glass',
                'difficulty': 'Medium',
                'prep_time_minutes': 4,
                'serving_size_ml': 90.0,
                'ingredients': [
                    {'ingredient_name': 'Blended Scotch Whisky', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Whisky', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Fresh Lemon Juice', 'ingredient_type': 'mixer', 'amount': 22.5, 'unit': 'ml'},
                    {'ingredient_name': 'Honey Syrup', 'ingredient_type': 'mixer', 'amount': 22.5, 'unit': 'ml'},
                    {'ingredient_name': 'Ginger Liqueur', 'ingredient_type': 'alcohol', 'amount': 7.5, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                ]
            },
            {
                'name': 'Gold Rush',
                'category': 'Cocktail',
                'description': 'Bourbon cocktail with honey syrup and lemon',
                'instructions': '1. Shake bourbon, lemon juice, and honey syrup with ice\n2. Strain into glass over ice\n3. Garnish with lemon wheel',
                'garnish': 'Lemon wheel',
                'glass_type': 'Old Fashioned Glass',
                'difficulty': 'Easy',
                'prep_time_minutes': 3,
                'serving_size_ml': 90.0,
                'ingredients': [
                    {'ingredient_name': 'Bourbon Whiskey', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Whisky', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Fresh Lemon Juice', 'ingredient_type': 'mixer', 'amount': 22.5, 'unit': 'ml'},
                    {'ingredient_name': 'Honey Syrup', 'ingredient_type': 'mixer', 'amount': 22.5, 'unit': 'ml'},
                ]
            },
            {
                'name': 'Jungle Bird',
                'category': 'Cocktail',
                'description': 'Malaysian rum cocktail with Campari and pineapple',
                'instructions': '1. Shake all ingredients with ice\n2. Strain into glass over ice\n3. Garnish with pineapple wedge',
                'garnish': 'Pineapple wedge',
                'glass_type': 'Old Fashioned Glass',
                'difficulty': 'Medium',
                'prep_time_minutes': 3,
                'serving_size_ml': 150.0,
                'ingredients': [
                    {'ingredient_name': 'Dark Rum', 'ingredient_type': 'alcohol', 'amount': 45, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Rum', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Campari', 'ingredient_type': 'alcohol', 'amount': 22.5, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                    {'ingredient_name': 'Pineapple Juice', 'ingredient_type': 'mixer', 'amount': 45, 'unit': 'ml'},
                    {'ingredient_name': 'Fresh Lime Juice', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                    {'ingredient_name': 'Simple Syrup', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                ]
            },
            {
                'name': 'Tommy\'s Margarita',
                'category': 'Cocktail',
                'description': 'Agave-sweetened margarita variation',
                'instructions': '1. Shake tequila, lime juice, and agave nectar with ice\n2. Strain into glass over ice\n3. Garnish with lime wheel',
                'garnish': 'Lime wheel',
                'glass_type': 'Old Fashioned Glass',
                'difficulty': 'Easy',
                'prep_time_minutes': 2,
                'serving_size_ml': 90.0,
                'ingredients': [
                    {'ingredient_name': 'Silver Tequila', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Tequila', 'min_alcohol_percentage': 38.0},
                    {'ingredient_name': 'Fresh Lime Juice', 'ingredient_type': 'mixer', 'amount': 30, 'unit': 'ml'},
                    {'ingredient_name': 'Agave Nectar', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                ]
            },
            {
                'name': 'Rusty Nail',
                'category': 'Cocktail',
                'description': 'Scotch cocktail with Drambuie',
                'instructions': '1. Add scotch and Drambuie to glass with ice\n2. Stir gently\n3. Garnish with lemon twist',
                'garnish': 'Lemon twist',
                'glass_type': 'Old Fashioned Glass',
                'difficulty': 'Easy',
                'prep_time_minutes': 2,
                'serving_size_ml': 75.0,
                'ingredients': [
                    {'ingredient_name': 'Blended Scotch Whisky', 'ingredient_type': 'alcohol', 'amount': 45, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Whisky', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Drambuie', 'ingredient_type': 'alcohol', 'amount': 22.5, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                ]
            },
            {
                'name': 'Sidecar',
                'category': 'Cocktail',
                'description': 'Cognac cocktail with orange liqueur and lemon',
                'instructions': '1. Shake cognac, cointreau, and lemon juice with ice\n2. Strain into sugar-rimmed coupe\n3. Garnish with orange peel',
                'garnish': 'Orange peel',
                'glass_type': 'Coupe Glass',
                'difficulty': 'Medium',
                'prep_time_minutes': 3,
                'serving_size_ml': 75.0,
                'ingredients': [
                    {'ingredient_name': 'Cognac', 'ingredient_type': 'alcohol', 'amount': 50, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Brandy', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Cointreau', 'ingredient_type': 'alcohol', 'amount': 20, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                    {'ingredient_name': 'Fresh Lemon Juice', 'ingredient_type': 'mixer', 'amount': 20, 'unit': 'ml'},
                ]
            },
            {
                'name': 'Vieux Carré',
                'category': 'Cocktail',
                'description': 'New Orleans cocktail with rye, cognac, and vermouth',
                'instructions': '1. Stir all ingredients with ice\n2. Strain into old fashioned glass over ice\n3. Garnish with cherry',
                'garnish': 'Maraschino cherry',
                'glass_type': 'Old Fashioned Glass',
                'difficulty': 'Hard',
                'prep_time_minutes': 4,
                'serving_size_ml': 90.0,
                'ingredients': [
                    {'ingredient_name': 'Rye Whiskey', 'ingredient_type': 'alcohol', 'amount': 30, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Whisky', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Cognac', 'ingredient_type': 'alcohol', 'amount': 30, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Brandy', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Sweet Vermouth', 'ingredient_type': 'alcohol', 'amount': 30, 'unit': 'ml', 'alcohol_category': 'Wine', 'alcohol_subcategory': 'Vermouth'},
                    {'ingredient_name': 'Benedictine', 'ingredient_type': 'alcohol', 'amount': 15, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                    {'ingredient_name': 'Peychauds Bitters', 'ingredient_type': 'mixer', 'amount': 2, 'unit': 'dash'},
                ]
            },
            {
                'name': 'White Russian',
                'category': 'Cocktail',
                'description': 'Vodka cocktail with coffee liqueur and cream',
                'instructions': '1. Add vodka and coffee liqueur to glass with ice\n2. Float cream on top\n3. Stir gently if desired',
                'garnish': None,
                'glass_type': 'Old Fashioned Glass',
                'difficulty': 'Easy',
                'prep_time_minutes': 2,
                'serving_size_ml': 120.0,
                'ingredients': [
                    {'ingredient_name': 'Vodka', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Vodka', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Coffee Liqueur', 'ingredient_type': 'alcohol', 'amount': 30, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                    {'ingredient_name': 'Heavy Cream', 'ingredient_type': 'mixer', 'amount': 30, 'unit': 'ml'},
                ]
            },
            {
                'name': 'Black Russian',
                'category': 'Cocktail',
                'description': 'Vodka cocktail with coffee liqueur',
                'instructions': '1. Add vodka and coffee liqueur to glass with ice\n2. Stir gently',
                'garnish': None,
                'glass_type': 'Old Fashioned Glass',
                'difficulty': 'Easy',
                'prep_time_minutes': 1,
                'serving_size_ml': 90.0,
                'ingredients': [
                    {'ingredient_name': 'Vodka', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Vodka', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Coffee Liqueur', 'ingredient_type': 'alcohol', 'amount': 30, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                ]
            },
            {
                'name': 'Godfather',
                'category': 'Cocktail',
                'description': 'Scotch cocktail with amaretto',
                'instructions': '1. Add scotch and amaretto to glass with ice\n2. Stir gently',
                'garnish': None,
                'glass_type': 'Old Fashioned Glass',
                'difficulty': 'Easy',
                'prep_time_minutes': 1,
                'serving_size_ml': 75.0,
                'ingredients': [
                    {'ingredient_name': 'Blended Scotch Whisky', 'ingredient_type': 'alcohol', 'amount': 45, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Whisky', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Amaretto', 'ingredient_type': 'alcohol', 'amount': 22.5, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                ]
            },
            {
                'name': 'Bramble',
                'category': 'Cocktail',
                'description': 'Gin cocktail with blackberry liqueur',
                'instructions': '1. Shake gin and lemon juice with ice\n2. Strain into glass over crushed ice\n3. Drizzle blackberry liqueur over top\n4. Garnish with blackberries',
                'garnish': 'Fresh blackberries',
                'glass_type': 'Old Fashioned Glass',
                'difficulty': 'Medium',
                'prep_time_minutes': 3,
                'serving_size_ml': 90.0,
                'ingredients': [
                    {'ingredient_name': 'London Dry Gin', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Gin', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Fresh Lemon Juice', 'ingredient_type': 'mixer', 'amount': 25, 'unit': 'ml'},
                    {'ingredient_name': 'Simple Syrup', 'ingredient_type': 'mixer', 'amount': 12.5, 'unit': 'ml'},
                    {'ingredient_name': 'Blackberry Liqueur', 'ingredient_type': 'alcohol', 'amount': 15, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                ]
            },
            {
                'name': 'Last Word',
                'category': 'Cocktail',
                'description': 'Equal parts gin cocktail with green chartreuse',
                'instructions': '1. Shake all ingredients with ice\n2. Strain into chilled coupe\n3. No garnish',
                'garnish': None,
                'glass_type': 'Coupe Glass',
                'difficulty': 'Medium',
                'prep_time_minutes': 3,
                'serving_size_ml': 90.0,
                'ingredients': [
                    {'ingredient_name': 'London Dry Gin', 'ingredient_type': 'alcohol', 'amount': 22.5, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Gin', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Green Chartreuse', 'ingredient_type': 'alcohol', 'amount': 22.5, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                    {'ingredient_name': 'Maraschino Liqueur', 'ingredient_type': 'alcohol', 'amount': 22.5, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                    {'ingredient_name': 'Fresh Lime Juice', 'ingredient_type': 'mixer', 'amount': 22.5, 'unit': 'ml'},
                ]
            },
            {
                'name': 'Clover Club',
                'category': 'Cocktail',
                'description': 'Gin cocktail with raspberry syrup and egg white',
                'instructions': '1. Dry shake all ingredients\n2. Shake with ice\n3. Strain into chilled coupe\n4. Garnish with raspberries',
                'garnish': 'Fresh raspberries',
                'glass_type': 'Coupe Glass',
                'difficulty': 'Medium',
                'prep_time_minutes': 4,
                'serving_size_ml': 90.0,
                'ingredients': [
                    {'ingredient_name': 'London Dry Gin', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Gin', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Fresh Lemon Juice', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                    {'ingredient_name': 'Raspberry Syrup', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                    {'ingredient_name': 'Egg White', 'ingredient_type': 'mixer', 'amount': 1, 'unit': 'whole'},
                ]
            },
            {
                'name': 'Scofflaw',
                'category': 'Cocktail',
                'description': 'Rye whiskey cocktail with dry vermouth and lemon',
                'instructions': '1. Shake all ingredients with ice\n2. Strain into chilled coupe\n3. Garnish with lemon twist',
                'garnish': 'Lemon twist',
                'glass_type': 'Coupe Glass',
                'difficulty': 'Medium',
                'prep_time_minutes': 3,
                'serving_size_ml': 90.0,
                'ingredients': [
                    {'ingredient_name': 'Rye Whiskey', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Whisky', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Dry Vermouth', 'ingredient_type': 'alcohol', 'amount': 22.5, 'unit': 'ml', 'alcohol_category': 'Wine', 'alcohol_subcategory': 'Vermouth'},
                    {'ingredient_name': 'Fresh Lemon Juice', 'ingredient_type': 'mixer', 'amount': 22.5, 'unit': 'ml'},
                    {'ingredient_name': 'Grenadine', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                    {'ingredient_name': 'Orange Bitters', 'ingredient_type': 'mixer', 'amount': 2, 'unit': 'dash'},
                ]
            },
            {
                'name': 'Southside',
                'category': 'Cocktail',
                'description': 'Gin cocktail with mint and lime juice',
                'instructions': '1. Muddle mint gently\n2. Shake gin, lime juice, and simple syrup with ice\n3. Strain into chilled coupe\n4. Garnish with mint sprig',
                'garnish': 'Fresh mint sprig',
                'glass_type': 'Coupe Glass',
                'difficulty': 'Medium',
                'prep_time_minutes': 4,
                'serving_size_ml': 90.0,
                'ingredients': [
                    {'ingredient_name': 'London Dry Gin', 'ingredient_type': 'alcohol', 'amount': 60, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Gin', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Fresh Lime Juice', 'ingredient_type': 'mixer', 'amount': 30, 'unit': 'ml'},
                    {'ingredient_name': 'Simple Syrup', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                    {'ingredient_name': 'Fresh Mint Leaves', 'ingredient_type': 'garnish', 'amount': 6, 'unit': 'leaves'},
                ]
            },
            {
                'name': 'Hanky Panky',
                'category': 'Cocktail',
                'description': 'Gin and vermouth cocktail with Fernet-Branca',
                'instructions': '1. Stir gin, vermouth, and Fernet-Branca with ice\n2. Strain into chilled coupe\n3. Garnish with orange peel',
                'garnish': 'Orange peel',
                'glass_type': 'Coupe Glass',
                'difficulty': 'Medium',
                'prep_time_minutes': 3,
                'serving_size_ml': 75.0,
                'ingredients': [
                    {'ingredient_name': 'London Dry Gin', 'ingredient_type': 'alcohol', 'amount': 45, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Gin', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Sweet Vermouth', 'ingredient_type': 'alcohol', 'amount': 45, 'unit': 'ml', 'alcohol_category': 'Wine', 'alcohol_subcategory': 'Vermouth'},
                    {'ingredient_name': 'Fernet-Branca', 'ingredient_type': 'alcohol', 'amount': 7.5, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                ]
            },
            {
                'name': 'Naked and Famous',
                'category': 'Cocktail',
                'description': 'Equal parts mezcal cocktail with yellow chartreuse',
                'instructions': '1. Shake all ingredients with ice\n2. Strain into chilled coupe\n3. Garnish with lime wheel',
                'garnish': 'Lime wheel',
                'glass_type': 'Coupe Glass',
                'difficulty': 'Medium',
                'prep_time_minutes': 3,
                'serving_size_ml': 90.0,
                'ingredients': [
                    {'ingredient_name': 'Mezcal', 'ingredient_type': 'alcohol', 'amount': 22.5, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Tequila', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Yellow Chartreuse', 'ingredient_type': 'alcohol', 'amount': 22.5, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                    {'ingredient_name': 'Aperol', 'ingredient_type': 'alcohol', 'amount': 22.5, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                    {'ingredient_name': 'Fresh Lime Juice', 'ingredient_type': 'mixer', 'amount': 22.5, 'unit': 'ml'},
                ]
            },
            {
                'name': 'Smoke and Mirrors',
                'category': 'Cocktail',
                'description': 'Mezcal cocktail with yellow chartreuse and pineapple',
                'instructions': '1. Shake all ingredients with ice\n2. Strain into glass over ice\n3. Garnish with pineapple wedge',
                'garnish': 'Pineapple wedge',
                'glass_type': 'Old Fashioned Glass',
                'difficulty': 'Medium',
                'prep_time_minutes': 3,
                'serving_size_ml': 120.0,
                'ingredients': [
                    {'ingredient_name': 'Mezcal', 'ingredient_type': 'alcohol', 'amount': 45, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Tequila', 'min_alcohol_percentage': 40.0},
                    {'ingredient_name': 'Yellow Chartreuse', 'ingredient_type': 'alcohol', 'amount': 15, 'unit': 'ml', 'alcohol_category': 'Spirits', 'alcohol_subcategory': 'Liqueur'},
                    {'ingredient_name': 'Pineapple Juice', 'ingredient_type': 'mixer', 'amount': 45, 'unit': 'ml'},
                    {'ingredient_name': 'Fresh Lime Juice', 'ingredient_type': 'mixer', 'amount': 15, 'unit': 'ml'},
                ]
            }
        ]
        
        loaded_count = 0
        for recipe_data in default_recipes:
            # Check if recipe already exists
            existing = self.find_recipe_by_name(recipe_data['name'])
            if not existing:
                if self.create_recipe(recipe_data):
                    loaded_count += 1
            else:
                logger.info(f"Recipe '{recipe_data['name']}' already exists, skipping")
        
        logger.info(f"Loaded {loaded_count} new default recipes")
        return loaded_count
    
    def get_all_recipes(self) -> List[Recipe]:
        """Get all active recipes"""
        with get_session() as session:
            recipes = session.query(Recipe).filter_by(is_active=True).all()
            # Detach from session to avoid lazy loading issues
            for recipe in recipes:
                session.expunge(recipe)
            return recipes
    
    def update_recipe(self, recipe_id: int, updates: Dict) -> bool:
        """Update an existing recipe"""
        with get_session() as session:
            try:
                recipe = session.query(Recipe).filter_by(id=recipe_id).first()
                if not recipe:
                    return False
                
                for key, value in updates.items():
                    if hasattr(recipe, key):
                        setattr(recipe, key, value)
                
                session.commit()
                logger.info(f"Updated recipe: {recipe.name}")
                return True
                
            except Exception as e:
                logger.error(f"Error updating recipe {recipe_id}: {e}")
                session.rollback()
                return False
    
    def delete_recipe(self, recipe_id: int) -> bool:
        """Soft delete a recipe"""
        with get_session() as session:
            try:
                recipe = session.query(Recipe).filter_by(id=recipe_id).first()
                if not recipe:
                    return False
                
                recipe.is_active = False
                session.commit()
                logger.info(f"Deleted recipe: {recipe.name}")
                return True
                
            except Exception as e:
                logger.error(f"Error deleting recipe {recipe_id}: {e}")
                session.rollback()
                return False