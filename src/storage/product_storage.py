from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from src.models import Product, PriceHistory, Inventory, StoreInventory, get_session
from src.utils import logger

class ProductStorage:
    def __init__(self):
        pass
    
    def save_product(self, product_data: Dict) -> Optional[Product]:
        with get_session() as session:
            try:
                existing_product = session.query(Product).filter_by(
                    lcbo_id=product_data.get('lcbo_id')
                ).first()
                
                if existing_product:
                    updated = self._update_product(session, existing_product, product_data)
                    if updated:
                        logger.info(f"Updated product: {existing_product.name}")
                    return existing_product
                else:
                    new_product = self._create_product(session, product_data)
                    logger.info(f"Created new product: {new_product.name}")
                    return new_product
                    
            except Exception as e:
                logger.error(f"Error saving product: {e}")
                session.rollback()
                return None
    
    def save_products_batch(self, products_data: List[Dict]) -> int:
        saved_count = 0
        
        with get_session() as session:
            for product_data in products_data:
                try:
                    existing_product = session.query(Product).filter_by(
                        lcbo_id=product_data.get('lcbo_id')
                    ).first()
                    
                    if existing_product:
                        if self._update_product(session, existing_product, product_data):
                            saved_count += 1
                    else:
                        self._create_product(session, product_data)
                        saved_count += 1
                        
                except Exception as e:
                    logger.error(f"Error saving product {product_data.get('lcbo_id')}: {e}")
                    continue
            
            try:
                session.commit()
                logger.info(f"Batch saved {saved_count} products")
            except Exception as e:
                logger.error(f"Error committing batch: {e}")
                session.rollback()
                saved_count = 0
        
        return saved_count
    
    def _create_product(self, session: Session, product_data: Dict) -> Product:
        product = Product(
            lcbo_id=product_data.get('lcbo_id'),
            name=product_data.get('name'),
            brand=product_data.get('brand'),
            category=product_data.get('category'),
            subcategory=product_data.get('subcategory'),
            price=product_data.get('price'),
            regular_price=product_data.get('regular_price'),
            volume_ml=product_data.get('volume_ml'),
            alcohol_percentage=product_data.get('alcohol_percentage'),
            country=product_data.get('country'),
            region=product_data.get('region'),
            description=product_data.get('description'),
            image_url=product_data.get('image_url'),
            product_url=product_data.get('product_url'),
            is_active=True
        )
        
        session.add(product)
        session.flush()
        
        if product.price:
            self._add_price_history(session, product.id, product.price, product.regular_price)
        
        inventory_data = product_data.get('inventory')
        if inventory_data:
            self._update_inventory(session, product.id, inventory_data)
        
        # Save store inventory data if available
        store_inventory = product_data.get('store_inventory')
        if store_inventory:
            self._save_store_inventory_data(session, product.lcbo_id, store_inventory)
        
        return product
    
    def _update_product(self, session: Session, product: Product, product_data: Dict) -> bool:
        updated = False
        price_changed = False
        
        fields_to_update = [
            'name', 'brand', 'category', 'subcategory', 'volume_ml',
            'alcohol_percentage', 'country', 'region', 'description',
            'image_url', 'product_url'
        ]
        
        for field in fields_to_update:
            new_value = product_data.get(field)
            if new_value and getattr(product, field) != new_value:
                setattr(product, field, new_value)
                updated = True
        
        new_price = product_data.get('price')
        if new_price and product.price != new_price:
            product.price = new_price
            product.regular_price = product_data.get('regular_price')
            price_changed = True
            updated = True
        
        if updated:
            product.last_updated = datetime.utcnow()
        
        if price_changed:
            self._add_price_history(session, product.id, product.price, product.regular_price)
        
        inventory_data = product_data.get('inventory')
        if inventory_data:
            self._update_inventory(session, product.id, inventory_data)
        
        # Save store inventory data if available
        store_inventory = product_data.get('store_inventory')
        if store_inventory:
            self._save_store_inventory_data(session, product.lcbo_id, store_inventory)
        
        return updated
    
    def _add_price_history(self, session: Session, product_id: int, price: float, regular_price: float = None):
        price_history = PriceHistory(
            product_id=product_id,
            price=price,
            regular_price=regular_price
        )
        session.add(price_history)
    
    def _update_inventory(self, session: Session, product_id: int, inventory_data: Dict):
        inventory = session.query(Inventory).filter_by(
            product_id=product_id,
            store_id='online'
        ).first()
        
        if not inventory:
            inventory = Inventory(
                product_id=product_id,
                store_id='online',
                store_name='LCBO Online'
            )
            session.add(inventory)
        
        inventory.is_online_available = inventory_data.get('online_available', True)
        inventory.quantity = inventory_data.get('quantity')
        inventory.last_checked = datetime.utcnow()
    
    def get_product_by_lcbo_id(self, lcbo_id: str) -> Optional[Product]:
        with get_session() as session:
            return session.query(Product).filter_by(lcbo_id=lcbo_id).first()
    
    def get_products_by_category(self, category: str, limit: int = None) -> List[Product]:
        with get_session() as session:
            query = session.query(Product).filter_by(category=category, is_active=True)
            if limit:
                query = query.limit(limit)
            return query.all()
    
    def get_all_products(self, limit: int = None) -> List[Product]:
        with get_session() as session:
            query = session.query(Product).filter_by(is_active=True)
            if limit:
                query = query.limit(limit)
            return query.all()
    
    def get_price_history(self, product_id: int, days: int = 30) -> List[PriceHistory]:
        with get_session() as session:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            return session.query(PriceHistory).filter(
                PriceHistory.product_id == product_id,
                PriceHistory.recorded_at >= cutoff_date
            ).order_by(PriceHistory.recorded_at.desc()).all()
    
    def mark_inactive_products(self, active_lcbo_ids: List[str]):
        with get_session() as session:
            session.query(Product).filter(
                ~Product.lcbo_id.in_(active_lcbo_ids)
            ).update(
                {Product.is_active: False},
                synchronize_session=False
            )
            session.commit()
            logger.info(f"Marked products as inactive except for {len(active_lcbo_ids)} active IDs")
    
    def _save_store_inventory_data(self, session: Session, product_lcbo_id: str, store_inventory: Dict):
        """Save general store inventory flags to a generic 'general' store entry"""
        try:
            # Save to a generic "general" store to track overall store availability
            general_store_id = "general"
            
            existing = session.query(StoreInventory).filter_by(
                store_id=general_store_id,
                product_lcbo_id=product_lcbo_id
            ).first()
            
            if existing:
                existing.in_stock = store_inventory.get('stores_stock_combined', False)
                existing.low_stock = store_inventory.get('stores_low_stock_combined', False)
                existing.last_checked = datetime.utcnow()
            else:
                inventory = StoreInventory(
                    store_id=general_store_id,
                    product_lcbo_id=product_lcbo_id,
                    in_stock=store_inventory.get('stores_stock_combined', False),
                    low_stock=store_inventory.get('stores_low_stock_combined', False),
                    quantity=0  # We don't have specific quantity data
                )
                session.add(inventory)
            
        except Exception as e:
            logger.debug(f"Error saving store inventory data: {e}")