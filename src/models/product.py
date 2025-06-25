from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from .database import Base

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True)
    lcbo_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    brand = Column(String(255))
    category = Column(String(100))
    subcategory = Column(String(100))
    price = Column(Float)
    regular_price = Column(Float)
    volume_ml = Column(Integer)
    alcohol_percentage = Column(Float)
    country = Column(String(100))
    region = Column(String(100))
    description = Column(Text)
    image_url = Column(String(500))
    product_url = Column(String(500))
    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    price_history = relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan")
    inventory = relationship("Inventory", back_populates="product", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Product(lcbo_id={self.lcbo_id}, name={self.name}, price=${self.price})>"

class PriceHistory(Base):
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    price = Column(Float, nullable=False)
    regular_price = Column(Float)
    recorded_at = Column(DateTime, default=datetime.utcnow)
    
    product = relationship("Product", back_populates="price_history")
    
    def __repr__(self):
        return f"<PriceHistory(product_id={self.product_id}, price=${self.price}, date={self.recorded_at})>"

class Inventory(Base):
    __tablename__ = "inventory"
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    store_id = Column(String(50))
    store_name = Column(String(255))
    quantity = Column(Integer)
    is_online_available = Column(Boolean, default=True)
    last_checked = Column(DateTime, default=datetime.utcnow)
    
    product = relationship("Product", back_populates="inventory")
    
    def __repr__(self):
        return f"<Inventory(product_id={self.product_id}, store={self.store_name}, qty={self.quantity})>"