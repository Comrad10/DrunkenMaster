from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class Store(Base):
    __tablename__ = "stores"
    
    id = Column(Integer, primary_key=True)
    store_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    address = Column(String(500))
    city = Column(String(100))
    province = Column(String(50))
    postal_code = Column(String(20))
    phone = Column(String(50))
    latitude = Column(Float)
    longitude = Column(Float)
    store_type = Column(String(100))  # Regular, Wine Boutique, etc.
    hours = Column(Text)  # JSON string of operating hours
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to inventory
    inventory_items = relationship("StoreInventory", back_populates="store", cascade="all, delete-orphan", 
                                  primaryjoin="Store.store_id == StoreInventory.store_id", foreign_keys="StoreInventory.store_id")
    
    def __repr__(self):
        return f"<Store(store_id={self.store_id}, name={self.name}, city={self.city})>"

class StoreInventory(Base):
    __tablename__ = "store_inventory"
    
    id = Column(Integer, primary_key=True)
    store_id = Column(String(50), nullable=False, index=True)
    product_lcbo_id = Column(String(50), nullable=False, index=True)
    quantity = Column(Integer, default=0)
    in_stock = Column(Boolean, default=False)
    low_stock = Column(Boolean, default=False)
    last_checked = Column(DateTime, default=datetime.utcnow)
    
    # Relationships  
    store = relationship("Store", back_populates="inventory_items", 
                        primaryjoin="Store.store_id == StoreInventory.store_id", foreign_keys=[store_id])
    
    def __repr__(self):
        return f"<StoreInventory(store_id={self.store_id}, product_id={self.product_lcbo_id}, in_stock={self.in_stock})>"