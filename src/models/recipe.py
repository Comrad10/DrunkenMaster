from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Recipe(Base):
    __tablename__ = "recipes"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, index=True)
    category = Column(String(100))  # Cocktail, Shot, Beer Cocktail, etc.
    description = Column(Text)
    instructions = Column(Text)
    garnish = Column(String(255))
    glass_type = Column(String(100))
    difficulty = Column(String(50))  # Easy, Medium, Hard
    prep_time_minutes = Column(Integer)
    serving_size_ml = Column(Float, default=120.0)  # Standard cocktail size
    
    # Metadata
    source = Column(String(255))  # Recipe source/attribution
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    ingredients = relationship("RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan")
    cost_calculations = relationship("DrinkCostCalculation", back_populates="recipe")

class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"
    
    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    
    # Ingredient details
    ingredient_name = Column(String(255), nullable=False)  # e.g., "Vodka", "Triple Sec", "Lime Juice"
    ingredient_type = Column(String(100))  # alcohol, mixer, garnish, etc.
    
    # Amount specifications
    amount = Column(Float, nullable=False)  # Numeric amount
    unit = Column(String(50), nullable=False)  # ml, oz, dash, splash, etc.
    amount_ml = Column(Float)  # Converted to ml for calculations
    
    # LCBO product matching
    preferred_lcbo_product = Column(String(50))  # LCBO ID if known
    alcohol_category = Column(String(100))  # Spirits, Wine, Beer, etc.
    alcohol_subcategory = Column(String(100))  # Vodka, Whisky, etc.
    min_alcohol_percentage = Column(Float)  # Minimum ABV required
    
    # Optional specifications
    brand_preference = Column(String(255))  # Preferred brand if any
    notes = Column(Text)  # Special notes about the ingredient
    
    created_at = Column(DateTime, default=datetime.utcnow)
    is_essential = Column(Boolean, default=True)  # Can recipe work without this?
    
    # Relationships
    recipe = relationship("Recipe", back_populates="ingredients")

class DrinkCostCalculation(Base):
    __tablename__ = "drink_cost_calculations"
    
    id = Column(Integer, primary_key=True)
    recipe_id = Column(Integer, ForeignKey("recipes.id"), nullable=False)
    
    # Calculation details
    total_alcohol_cost = Column(Float, nullable=False)  # Total cost of alcohol ingredients
    total_mixer_cost = Column(Float, default=0.0)  # Cost of non-alcohol ingredients
    total_cost = Column(Float, nullable=False)  # Total ingredient cost
    
    # Cost breakdown
    cost_per_ml = Column(Float)  # Cost per ml of finished drink
    markup_suggested = Column(Float)  # Suggested markup percentage
    suggested_selling_price = Column(Float)  # Suggested menu price
    
    # Market analysis
    lowest_cost_option = Column(Float)  # Cheapest way to make this drink
    premium_cost_option = Column(Float)  # Premium ingredient cost
    
    # Metadata
    calculation_date = Column(DateTime, default=datetime.utcnow)
    lcbo_data_date = Column(DateTime)  # When LCBO prices were last updated
    city = Column(String(100), default="St. Catharines")  # Store location used
    
    # Stock availability
    all_ingredients_available = Column(Boolean, default=False)
    missing_ingredients = Column(Text)  # JSON list of unavailable ingredients
    
    # Sale information
    ingredients_on_sale = Column(Text)  # JSON list of ingredients currently on sale
    total_sale_savings = Column(Float, default=0.0)
    
    # Relationships
    recipe = relationship("Recipe", back_populates="cost_calculations")
    ingredient_costs = relationship("IngredientCost", back_populates="calculation")

class IngredientCost(Base):
    __tablename__ = "ingredient_costs"
    
    id = Column(Integer, primary_key=True)
    calculation_id = Column(Integer, ForeignKey("drink_cost_calculations.id"), nullable=False)
    recipe_ingredient_id = Column(Integer, ForeignKey("recipe_ingredients.id"), nullable=False)
    
    # Product details
    lcbo_product_id = Column(String(50))  # Matched LCBO product
    product_name = Column(String(255))
    brand = Column(String(255))
    
    # Pricing
    product_price = Column(Float, nullable=False)  # Full bottle price
    product_volume_ml = Column(Float, nullable=False)  # Bottle size in ml
    price_per_ml = Column(Float, nullable=False)  # Price per ml
    
    # Sale information
    regular_price = Column(Float)  # Regular price (if on sale)
    is_on_sale = Column(Boolean, default=False)
    sale_savings = Column(Float, default=0.0)
    
    # Usage calculation
    amount_needed_ml = Column(Float, nullable=False)  # How much needed for recipe
    ingredient_cost = Column(Float, nullable=False)  # Cost for amount needed
    
    # Availability
    in_stock = Column(Boolean, default=False)
    stores_available = Column(Text)  # JSON list of stores with stock
    
    # Alternative options
    is_cheapest_option = Column(Boolean, default=False)
    is_premium_option = Column(Boolean, default=False)
    alternative_rank = Column(Integer)  # 1 = best option, 2 = second best, etc.
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    calculation = relationship("DrinkCostCalculation", back_populates="ingredient_costs")
    recipe_ingredient = relationship("RecipeIngredient")