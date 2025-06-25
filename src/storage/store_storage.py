from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from src.models import Store, StoreInventory, get_session
from src.utils import logger

class StoreStorage:
    def __init__(self):
        pass
    
    def save_store(self, store_data: Dict) -> Optional[Store]:
        """Save or update a single store"""
        with get_session() as session:
            try:
                existing_store = session.query(Store).filter_by(
                    store_id=store_data.get('store_id')
                ).first()
                
                if existing_store:
                    updated = self._update_store(session, existing_store, store_data)
                    if updated:
                        logger.info(f"Updated store: {existing_store.name}")
                    return existing_store
                else:
                    new_store = self._create_store(session, store_data)
                    logger.info(f"Created new store: {new_store.name}")
                    return new_store
                    
            except Exception as e:
                logger.error(f"Error saving store: {e}")
                session.rollback()
                return None
    
    def save_stores_batch(self, stores_data: List[Dict]) -> int:
        """Save multiple stores in batch"""
        saved_count = 0
        
        with get_session() as session:
            for store_data in stores_data:
                try:
                    existing_store = session.query(Store).filter_by(
                        store_id=store_data.get('store_id')
                    ).first()
                    
                    if existing_store:
                        if self._update_store(session, existing_store, store_data):
                            saved_count += 1
                    else:
                        self._create_store(session, store_data)
                        saved_count += 1
                        
                except Exception as e:
                    logger.error(f"Error saving store {store_data.get('store_id')}: {e}")
                    continue
            
            try:
                session.commit()
                logger.info(f"Batch saved {saved_count} stores")
            except Exception as e:
                logger.error(f"Error committing store batch: {e}")
                session.rollback()
                saved_count = 0
        
        return saved_count
    
    def _create_store(self, session: Session, store_data: Dict) -> Store:
        """Create a new store"""
        store = Store(
            store_id=store_data.get('store_id'),
            name=store_data.get('name'),
            address=store_data.get('address'),
            city=store_data.get('city'),
            province=store_data.get('province', 'ON'),
            postal_code=store_data.get('postal_code'),
            phone=store_data.get('phone'),
            latitude=store_data.get('latitude'),
            longitude=store_data.get('longitude'),
            store_type=store_data.get('store_type', 'Regular'),
            hours=store_data.get('hours'),
            is_active=True
        )
        
        session.add(store)
        session.flush()
        return store
    
    def _update_store(self, session: Session, store: Store, store_data: Dict) -> bool:
        """Update an existing store"""
        updated = False
        
        fields_to_update = [
            'name', 'address', 'city', 'province', 'postal_code',
            'phone', 'latitude', 'longitude', 'store_type', 'hours'
        ]
        
        for field in fields_to_update:
            new_value = store_data.get(field)
            if new_value and getattr(store, field) != new_value:
                setattr(store, field, new_value)
                updated = True
        
        if updated:
            store.last_updated = datetime.utcnow()
        
        return updated
    
    def save_store_inventory(self, store_id: str, product_lcbo_id: str, inventory_data: Dict) -> bool:
        """Save inventory data for a specific store and product"""
        with get_session() as session:
            try:
                existing_inventory = session.query(StoreInventory).filter_by(
                    store_id=store_id,
                    product_lcbo_id=product_lcbo_id
                ).first()
                
                if existing_inventory:
                    existing_inventory.quantity = inventory_data.get('quantity', 0)
                    existing_inventory.in_stock = inventory_data.get('in_stock', False)
                    existing_inventory.low_stock = inventory_data.get('low_stock', False)
                    existing_inventory.last_checked = datetime.utcnow()
                else:
                    inventory = StoreInventory(
                        store_id=store_id,
                        product_lcbo_id=product_lcbo_id,
                        quantity=inventory_data.get('quantity', 0),
                        in_stock=inventory_data.get('in_stock', False),
                        low_stock=inventory_data.get('low_stock', False)
                    )
                    session.add(inventory)
                
                session.commit()
                return True
                
            except Exception as e:
                logger.error(f"Error saving store inventory: {e}")
                session.rollback()
                return False
    
    def get_all_stores(self, city: str = None) -> List[Store]:
        """Get all stores, optionally filtered by city"""
        with get_session() as session:
            query = session.query(Store).filter_by(is_active=True)
            if city:
                query = query.filter(Store.city.ilike(f"%{city}%"))
            return query.all()
    
    def get_store_by_id(self, store_id: str) -> Optional[Store]:
        """Get a store by its ID"""
        with get_session() as session:
            return session.query(Store).filter_by(store_id=store_id, is_active=True).first()
    
    def get_product_availability(self, product_lcbo_id: str, city: str = None) -> List[Dict]:
        """Get availability of a product across stores"""
        with get_session() as session:
            # First, get all store inventory for this product
            inventory_items = session.query(StoreInventory).filter(
                StoreInventory.product_lcbo_id == product_lcbo_id
            ).all()
            
            availability = []
            for inventory in inventory_items:
                # Get store details if it's not the "general" store
                if inventory.store_id != "general":
                    store = session.query(Store).filter_by(
                        store_id=inventory.store_id,
                        is_active=True
                    ).first()
                    
                    if store and (not city or city.lower() in store.city.lower()):
                        availability.append({
                            'store_id': store.store_id,
                            'store_name': store.name,
                            'address': store.address,
                            'city': store.city,
                            'phone': store.phone,
                            'in_stock': inventory.in_stock,
                            'quantity': inventory.quantity,
                            'low_stock': inventory.low_stock,
                            'last_checked': inventory.last_checked
                        })
                else:
                    # For general store inventory, always show as "All Stores"
                    availability.append({
                        'store_id': 'general',
                        'store_name': 'All LCBO Stores (Combined)',
                        'address': 'Various Locations',
                        'city': 'Ontario',
                        'phone': 'N/A',
                        'in_stock': inventory.in_stock,
                        'quantity': inventory.quantity,
                        'low_stock': inventory.low_stock,
                        'last_checked': inventory.last_checked
                    })
            
            return availability
    
    def get_store_inventory(self, store_id: str, in_stock_only: bool = True) -> List[Dict]:
        """Get all products available at a specific store"""
        with get_session() as session:
            query = session.query(StoreInventory).filter_by(store_id=store_id)
            
            if in_stock_only:
                query = query.filter_by(in_stock=True)
            
            inventories = query.all()
            
            return [{
                'product_lcbo_id': inv.product_lcbo_id,
                'quantity': inv.quantity,
                'in_stock': inv.in_stock,
                'low_stock': inv.low_stock,
                'last_checked': inv.last_checked
            } for inv in inventories]