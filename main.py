#!/usr/bin/env python3
"""
LCBO Crawler - Personal Use Product Data Collection Tool

This tool crawls LCBO product data for personal use only.
It includes respectful rate limiting and follows best practices.
"""

import asyncio
import json
from pathlib import Path
from typing import List, Dict, Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.config import config
from src.models import init_database
from src.crawlers import CoveoAPIInvestigator, CategoryCrawler, ProductCrawler, StoreLocatorCrawler
from src.crawlers.product_inventory_crawler import ProductInventoryCrawler
from src.crawlers.store_inventory_crawler import StoreInventoryCrawler
from src.storage import ProductStorage, StoreStorage
from src.services.recipe_service import RecipeService
from src.services.cost_calculator import DrinkCostCalculator
from src.services.ingredient_service import IngredientService
from src.utils import logger

console = Console()

@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--config-file', '-c', help='Path to config file')
def cli(verbose: bool, config_file: Optional[str]):
    """LCBO Crawler - Personal use product data collection tool"""
    if verbose:
        logger.info("Verbose logging enabled")
    
    config.create_directories()

@cli.command()
def init():
    """Initialize the database and create tables"""
    console.print("[bold blue]Initializing database...[/bold blue]")
    
    try:
        init_database()
        console.print("[bold green]✓[/bold green] Database initialized successfully")
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Database initialization failed: {e}")
        logger.error(f"Database initialization failed: {e}")

@cli.command()
def investigate():
    """Investigate Coveo API endpoints and structure"""
    console.print("[bold blue]Investigating LCBO website structure...[/bold blue]")
    
    async def run_investigation():
        try:
            investigator = CoveoAPIInvestigator()
            await investigator.run()
            
            report_path = config.DATA_DIR / "coveo_api_investigation.json"
            if report_path.exists():
                console.print(f"[bold green]✓[/bold green] Investigation complete. Report saved to: {report_path}")
            else:
                console.print("[bold yellow]⚠[/bold yellow] Investigation completed but no report generated")
        
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Investigation failed: {e}")
            logger.error(f"Investigation failed: {e}")
    
    asyncio.run(run_investigation())

@cli.command()
@click.option('--category', '-c', default='wine', help='Category to crawl (wine, beer-cider, spirits, etc.)')
@click.option('--max-pages', '-p', default=10, help='Maximum pages to crawl')
@click.option('--save', '-s', is_flag=True, help='Save products to database')
def crawl_category(category: str, max_pages: int, save: bool):
    """Crawl products from a specific category"""
    console.print(f"[bold blue]Crawling category: {category}[/bold blue]")
    
    async def run_crawl():
        try:
            crawler = CategoryCrawler(category)
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task(f"Crawling {category}...", total=None)
                
                products = await crawler.run()
                
                progress.update(task, description=f"Found {len(products)} products")
            
            if products:
                console.print(f"[bold green]✓[/bold green] Found {len(products)} products")
                
                if save:
                    storage = ProductStorage()
                    saved_count = storage.save_products_batch(products)
                    console.print(f"[bold green]✓[/bold green] Saved {saved_count} products to database")
                else:
                    output_file = config.DATA_DIR / f"{category}_products.json"
                    with open(output_file, 'w') as f:
                        json.dump(products, f, indent=2, default=str)
                    console.print(f"[bold green]✓[/bold green] Products saved to: {output_file}")
            else:
                console.print("[bold yellow]⚠[/bold yellow] No products found")
        
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Crawling failed: {e}")
            logger.error(f"Category crawling failed: {e}")
    
    asyncio.run(run_crawl())

@cli.command()
@click.option('--all-categories', '-a', is_flag=True, help='Crawl all categories')
@click.option('--categories', '-c', multiple=True, help='Specific categories to crawl')
@click.option('--max-pages', '-p', default=10, help='Maximum pages per category')
def crawl_all(all_categories: bool, categories: List[str], max_pages: int):
    """Crawl all categories or specified categories"""
    if all_categories:
        target_categories = config.CATEGORIES
    elif categories:
        target_categories = list(categories)
    else:
        target_categories = config.CATEGORIES
    
    console.print(f"[bold blue]Crawling categories: {', '.join(target_categories)}[/bold blue]")
    
    async def run_crawl_all():
        storage = ProductStorage()
        total_products = 0
        
        for category in target_categories:
            try:
                console.print(f"\n[bold yellow]Processing category: {category}[/bold yellow]")
                
                crawler = CategoryCrawler(category)
                products = await crawler.run()
                
                if products:
                    saved_count = storage.save_products_batch(products)
                    total_products += saved_count
                    console.print(f"[bold green]✓[/bold green] {category}: {saved_count} products saved")
                else:
                    console.print(f"[bold yellow]⚠[/bold yellow] {category}: No products found")
            
            except Exception as e:
                console.print(f"[bold red]✗[/bold red] {category}: Failed - {e}")
                logger.error(f"Failed to crawl category {category}: {e}")
        
        console.print(f"\n[bold green]Crawling complete! Total products saved: {total_products}[/bold green]")
    
    asyncio.run(run_crawl_all())

@cli.command()
@click.option('--limit', '-l', default=20, help='Limit number of products to show')
@click.option('--category', '-c', help='Filter by category')
def list_products(limit: int, category: Optional[str]):
    """List products from the database"""
    try:
        from src.models import get_session, Product
        
        with get_session() as session:
            if category:
                products = session.query(Product).filter_by(category=category, is_active=True).limit(limit).all()
            else:
                products = session.query(Product).filter_by(is_active=True).limit(limit).all()
            
            if not products:
                console.print("[bold yellow]No products found in database[/bold yellow]")
                return
            
            table = Table(title=f"Products{f' - {category}' if category else ''}")
            table.add_column("LCBO ID", style="cyan")
            table.add_column("Name", style="white")
            table.add_column("Brand", style="green")
            table.add_column("Price", style="yellow")
            table.add_column("Category", style="blue")
            
            for product in products:
                table.add_row(
                    product.lcbo_id,
                    product.name[:50] + "..." if len(product.name) > 50 else product.name,
                    product.brand or "N/A",
                    f"${product.price:.2f}" if product.price else "N/A",
                    product.category or "N/A"
                )
            
            console.print(table)
    
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to list products: {e}")
        logger.error(f"Failed to list products: {e}")

@cli.command()
def stats():
    """Show database statistics"""
    try:
        storage = ProductStorage()
        
        from src.models import get_session
        with get_session() as session:
            from src.models import Product
            total_products = session.query(Product).filter_by(is_active=True).count()
            
            categories = session.query(Product.category).distinct().all()
            category_counts = {}
            
            for category in categories:
                if category[0]:
                    count = session.query(Product).filter_by(
                        category=category[0], 
                        is_active=True
                    ).count()
                    category_counts[category[0]] = count
        
        table = Table(title="Database Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        table.add_row("Total Products", str(total_products))
        table.add_row("Categories", str(len(category_counts)))
        
        for category, count in category_counts.items():
            table.add_row(f"  {category}", str(count))
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to get statistics: {e}")
        logger.error(f"Failed to get statistics: {e}")

@cli.command()
@click.option('--output', '-o', default='lcbo_export.json', help='Output file name')
def export(output: str):
    """Export all products to JSON file"""
    try:
        from src.models import get_session, Product
        
        with get_session() as session:
            products = session.query(Product).filter_by(is_active=True).all()
            
            export_data = []
            for product in products:
                export_data.append({
                    'lcbo_id': product.lcbo_id,
                    'name': product.name,
                    'brand': product.brand,
                    'category': product.category,
                    'subcategory': product.subcategory,
                    'price': product.price,
                    'regular_price': product.regular_price,
                    'volume_ml': product.volume_ml,
                    'alcohol_percentage': product.alcohol_percentage,
                    'country': product.country,
                    'region': product.region,
                    'description': product.description,
                    'image_url': product.image_url,
                    'product_url': product.product_url,
                    'last_updated': product.last_updated.isoformat() if product.last_updated else None
                })
            
            output_path = config.DATA_DIR / output
            with open(output_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            console.print(f"[bold green]✓[/bold green] Exported {len(export_data)} products to: {output_path}")
    
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Export failed: {e}")
        logger.error(f"Export failed: {e}")

@cli.command()
@click.option('--city', '-c', default='St. Catharines', help='City to search for stores')
@click.option('--save', '-s', is_flag=True, help='Save stores to database')
def find_stores(city: str, save: bool):
    """Find and optionally save LCBO stores in a city"""
    console.print(f"[bold blue]Finding LCBO stores in {city}...[/bold blue]")
    
    async def run_store_search():
        try:
            crawler = StoreLocatorCrawler()
            stores = await crawler.search_stores_by_city(city)
            
            if stores:
                console.print(f"[bold green]✓[/bold green] Found {len(stores)} stores")
                
                # Display stores in a table
                table = Table(title=f"LCBO Stores in {city}")
                table.add_column("Store ID", style="cyan")
                table.add_column("Name", style="white")
                table.add_column("Address", style="green")
                table.add_column("Phone", style="yellow")
                
                for store in stores:
                    table.add_row(
                        store.get('store_id', 'N/A'),
                        store.get('name', 'N/A'),
                        store.get('address', 'N/A'),
                        store.get('phone', 'N/A')
                    )
                
                console.print(table)
                
                if save:
                    storage = StoreStorage()
                    saved_count = storage.save_stores_batch(stores)
                    console.print(f"[bold green]✓[/bold green] Saved {saved_count} stores to database")
                else:
                    output_file = config.DATA_DIR / f"{city.lower().replace(' ', '_')}_stores.json"
                    with open(output_file, 'w') as f:
                        json.dump(stores, f, indent=2)
                    console.print(f"[bold green]✓[/bold green] Stores saved to: {output_file}")
            else:
                console.print("[bold yellow]⚠[/bold yellow] No stores found")
        
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Store search failed: {e}")
            logger.error(f"Store search failed: {e}")
    
    asyncio.run(run_store_search())

@cli.command()
@click.option('--city', '-c', help='Filter stores by city')
def list_stores(city: Optional[str]):
    """List stores from the database"""
    try:
        from src.models import get_session, Store
        
        with get_session() as session:
            query = session.query(Store).filter_by(is_active=True)
            if city:
                query = query.filter(Store.city.ilike(f"%{city}%"))
            stores = query.all()
            
            if not stores:
                console.print("[bold yellow]No stores found in database[/bold yellow]")
                return
            
            table = Table(title=f"Stores{f' in {city}' if city else ''}")
            table.add_column("Store ID", style="cyan")
            table.add_column("Name", style="white")
            table.add_column("City", style="green")
            table.add_column("Address", style="yellow")
            table.add_column("Phone", style="blue")
            
            for store in stores:
                table.add_row(
                    store.store_id,
                    store.name,
                    store.city or "N/A",
                    store.address[:50] + "..." if store.address and len(store.address) > 50 else store.address or "N/A",
                    store.phone or "N/A"
                )
            
            console.print(table)
    
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to list stores: {e}")
        logger.error(f"Failed to list stores: {e}")

@cli.command()
@click.argument('product_id')
@click.option('--city', '-c', default='St. Catharines', help='Check availability in specific city')
def check_availability(product_id: str, city: str):
    """Check product availability across stores"""
    try:
        storage = StoreStorage()
        availability = storage.get_product_availability(product_id, city)
        
        if not availability:
            console.print(f"[bold yellow]No availability data found for product {product_id}[/bold yellow]")
            return
        
        table = Table(title=f"Product {product_id} Availability in {city}")
        table.add_column("Store", style="cyan")
        table.add_column("Address", style="white")
        table.add_column("In Stock", style="green")
        table.add_column("Quantity", style="yellow")
        table.add_column("Low Stock", style="red")
        table.add_column("Last Checked", style="blue")
        
        for avail in availability:
            table.add_row(
                avail['store_name'],
                avail['address'][:40] + "..." if len(avail['address']) > 40 else avail['address'],
                "✓" if avail['in_stock'] else "✗",
                str(avail['quantity']) if avail['quantity'] else "N/A",
                "⚠" if avail['low_stock'] else "",
                avail['last_checked'].strftime('%Y-%m-%d %H:%M') if avail['last_checked'] else "N/A"
            )
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to check availability: {e}")
        logger.error(f"Failed to check availability: {e}")

@cli.command()
@click.argument('store_id')
@click.option('--in-stock-only', '-s', is_flag=True, help='Show only products in stock')
def store_inventory(store_id: str, in_stock_only: bool):
    """Show inventory for a specific store"""
    try:
        store_storage = StoreStorage()
        
        # Handle special case for "general" store
        if store_id == "general":
            inventory = store_storage.get_store_inventory(store_id, in_stock_only)
            
            if not inventory:
                console.print(f"[bold yellow]No inventory data found for general store availability[/bold yellow]")
                return
            
            console.print(f"[bold blue]General Store Availability (All LCBO Stores Combined)[/bold blue]")
            console.print(f"Based on LCBO API data for store availability across the system\n")
            
            store_name = "General Store Availability"
        else:
            from src.models import get_session, Store
            
            with get_session() as session:
                store = session.query(Store).filter_by(store_id=store_id, is_active=True).first()
                
                if not store:
                    console.print(f"[bold red]✗[/bold red] Store {store_id} not found")
                    return
                
                store_name = store.name
                store_address = store.address
                store_phone = store.phone
                
            inventory = store_storage.get_store_inventory(store_id, in_stock_only)
            
            if not inventory:
                console.print(f"[bold yellow]No inventory data found for store {store_name}[/bold yellow]")
                return
            
            console.print(f"[bold blue]Inventory for {store_name}[/bold blue]")
            console.print(f"Address: {store_address}")
            console.print(f"Phone: {store_phone}\n")
        
        table = Table(title=f"{store_name} Inventory")
        table.add_column("Product ID", style="cyan")
        table.add_column("In Stock", style="green")
        table.add_column("Quantity", style="yellow")
        table.add_column("Low Stock", style="red")
        table.add_column("Last Checked", style="blue")
        
        for item in inventory:
            table.add_row(
                item['product_lcbo_id'],
                "✓" if item['in_stock'] else "✗",
                str(item['quantity']) if item['quantity'] else "N/A",
                "⚠" if item['low_stock'] else "",
                item['last_checked'].strftime('%Y-%m-%d %H:%M') if item['last_checked'] else "N/A"
            )
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to get store inventory: {e}")
        logger.error(f"Failed to get store inventory: {e}")

@cli.command()
@click.argument('product_id')
@click.option('--stores', '-s', multiple=True, help='Specific store IDs to check')
def investigate_inventory(product_id: str, stores: List[str]):
    """Investigate store-specific inventory for a product"""
    console.print(f"[bold blue]Investigating store inventory for product {product_id}...[/bold blue]")
    
    async def run_investigation():
        try:
            crawler = ProductInventoryCrawler()
            store_ids = list(stores) if stores else ['522', '392', '115', '189', '343']  # St. Catharines stores
            
            result = await crawler.investigate_product_inventory(product_id, store_ids)
            
            if result.get('error'):
                console.print(f"[bold red]✗[/bold red] Investigation failed: {result['error']}")
                return
                
            console.print(f"[bold green]✓[/bold green] Investigation complete!")
            
            # Display results
            if result.get('availability_data'):
                console.print("\n[bold yellow]Availability Data Found:[/bold yellow]")
                for key, value in result['availability_data'].items():
                    console.print(f"  {key}: {value}")
                    
            if result.get('store_selector_data'):
                console.print("\n[bold yellow]Store Selector Data:[/bold yellow]")
                selector_data = result['store_selector_data']
                for key, value in selector_data.items():
                    if key == 'options' and isinstance(value, list):
                        console.print(f"  Available stores:")
                        for option in value:
                            console.print(f"    - {option.get('text', 'N/A')} ({option.get('value', 'N/A')})")
                    else:
                        console.print(f"  {key}: {value}")
            
            # Save detailed results
            output_file = config.DATA_DIR / f"inventory_investigation_{product_id}.json"
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            console.print(f"\n[bold blue]Detailed results saved to: {output_file}[/bold blue]")
                        
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Investigation failed: {e}")
            logger.error(f"Inventory investigation failed: {e}")
    
    asyncio.run(run_investigation())

@cli.command()
@click.argument('product_id')
@click.option('--stores', '-s', multiple=True, help='Specific store IDs to check')
def check_store_inventory(product_id: str, stores: List[str]):
    """Check product availability at specific stores using enhanced crawler"""
    console.print(f"[bold blue]Checking store inventory for product {product_id}...[/bold blue]")
    
    async def run_store_check():
        try:
            crawler = StoreInventoryCrawler()
            store_ids = list(stores) if stores else ['522', '392', '115', '189', '343']  # St. Catharines stores
            
            result = await crawler.check_product_at_stores(product_id, store_ids)
            
            if result.get('error'):
                console.print(f"[bold red]✗[/bold red] Store check failed: {result['error']}")
                return
                
            console.print(f"[bold green]✓[/bold green] Store inventory check complete!")
            
            # Display results in a table
            table = Table(title=f"Product {product_id} Store Availability")
            table.add_column("Store ID", style="cyan")
            table.add_column("In Stock", style="green")
            table.add_column("Pickup Available", style="yellow")
            table.add_column("Online Available", style="blue")
            table.add_column("Status", style="white")
            
            for store_id in result.get('stores_checked', []):
                availability = result['availability'].get(store_id, {})
                
                in_stock = "✓" if availability.get('in_stock') else "✗"
                pickup = "✓" if availability.get('pickup_available') else "✗"
                online = "✓" if availability.get('online_available') else "✗"
                
                status = "OK"
                if availability.get('error'):
                    status = f"Error: {availability['error'][:30]}..."
                elif availability.get('search_attempted'):
                    status = "Searched" if availability.get('store_selected') else "Not Found"
                
                table.add_row(store_id, in_stock, pickup, online, status)
            
            console.print(table)
            
            # Save detailed results
            output_file = config.DATA_DIR / f"store_inventory_check_{product_id}.json"
            with open(output_file, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            console.print(f"\n[bold blue]Detailed results saved to: {output_file}[/bold blue]")
                        
        except Exception as e:
            console.print(f"[bold red]✗[/bold red] Store check failed: {e}")
            logger.error(f"Store inventory check failed: {e}")
    
    asyncio.run(run_store_check())

@cli.command()
@click.argument('recipe_name')
@click.option('--category', '-cat', default='Cocktail', help='Recipe category')
@click.option('--glass', '-g', help='Glass type (e.g., Old Fashioned Glass, Martini Glass)')
@click.option('--difficulty', '-d', default='Medium', type=click.Choice(['Easy', 'Medium', 'Hard']), help='Difficulty level')
@click.option('--serving-size', '-s', default=120, type=int, help='Serving size in ml')
def create_recipe(recipe_name: str, category: str, glass: str, difficulty: str, serving_size: int):
    """Create a new cocktail recipe interactively"""
    console.print(f"[bold blue]Creating new recipe: {recipe_name}[/bold blue]")
    
    try:
        recipe_service = RecipeService()
        
        # Check if recipe already exists
        existing = recipe_service.find_recipe_by_name(recipe_name)
        if existing:
            console.print(f"[bold red]✗[/bold red] Recipe '{recipe_name}' already exists")
            if not click.confirm("Do you want to create it anyway with a different name?"):
                return
            recipe_name = click.prompt("Enter new recipe name")
        
        # Collect basic info
        console.print(f"\n[bold yellow]Recipe Details:[/bold yellow]")
        description = click.prompt("Description", default="", show_default=False) or None
        instructions = click.prompt("Instructions (use \\n for new lines)", default="", show_default=False) or None
        if instructions:
            instructions = instructions.replace('\\n', '\n')
        garnish = click.prompt("Garnish", default="", show_default=False) or None
        prep_time = click.prompt("Prep time (minutes)", type=int, default=3)
        
        # Collect ingredients
        console.print(f"\n[bold yellow]Adding Ingredients:[/bold yellow]")
        console.print("Enter ingredients one by one. Press Enter with no input when done.")
        console.print("Format examples:")
        console.print("  - 60ml Vodka")
        console.print("  - 2 dash Angostura Bitters") 
        console.print("  - 30ml Fresh Lime Juice")
        
        ingredients = []
        ingredient_num = 1
        
        while True:
            ingredient_input = click.prompt(f"Ingredient #{ingredient_num}", default="", show_default=False)
            if not ingredient_input:
                break
                
            # Parse ingredient input
            parsed = _parse_ingredient_input(ingredient_input)
            if parsed:
                # Ask for additional details
                console.print(f"  Parsed: {parsed['amount']}{parsed['unit']} {parsed['ingredient_name']}")
                
                ingredient_type = click.prompt("  Type", default="alcohol" if any(word in parsed['ingredient_name'].lower() for word in ['vodka', 'gin', 'rum', 'whiskey', 'whisky', 'tequila', 'brandy', 'liqueur', 'wine', 'beer']) else "mixer", 
                                             type=click.Choice(['alcohol', 'mixer', 'garnish']))
                
                if ingredient_type == 'alcohol':
                    # Get alcohol-specific details
                    categories = ['Spirits', 'Wine', 'Beer & Cider']
                    category_choice = click.prompt("  Alcohol Category", default="Spirits", type=click.Choice(categories))
                    
                    subcategories = {
                        'Spirits': ['Vodka', 'Gin', 'Rum', 'Whisky', 'Tequila', 'Brandy', 'Liqueur'],
                        'Wine': ['Red Wine', 'White Wine', 'Sparkling Wine', 'Vermouth'],
                        'Beer & Cider': ['Beer', 'Cider']
                    }
                    
                    subcategory_choice = None
                    if category_choice in subcategories:
                        subcategory_choice = click.prompt("  Subcategory", default="", type=click.Choice(subcategories[category_choice] + [""]), show_default=False) or None
                    
                    min_abv = click.prompt("  Minimum ABV %", type=float, default=40.0) if category_choice == 'Spirits' else None
                    brand_pref = click.prompt("  Preferred brand (optional)", default="", show_default=False) or None
                    
                    parsed.update({
                        'ingredient_type': ingredient_type,
                        'alcohol_category': category_choice,
                        'alcohol_subcategory': subcategory_choice,
                        'min_alcohol_percentage': min_abv,
                        'brand_preference': brand_pref
                    })
                else:
                    parsed['ingredient_type'] = ingredient_type
                
                ingredients.append(parsed)
                ingredient_num += 1
                console.print(f"  [bold green]✓[/bold green] Added {parsed['ingredient_name']}")
            else:
                console.print(f"  [bold red]✗[/bold red] Could not parse ingredient. Try format: '60ml Vodka'")
        
        if not ingredients:
            console.print("[bold red]✗[/bold red] No ingredients added. Recipe creation cancelled.")
            return
        
        # Create recipe
        recipe_data = {
            'name': recipe_name,
            'category': category,
            'description': description,
            'instructions': instructions,
            'garnish': garnish,
            'glass_type': glass,
            'difficulty': difficulty,
            'prep_time_minutes': prep_time,
            'serving_size_ml': float(serving_size),
            'ingredients': ingredients
        }
        
        recipe = recipe_service.create_recipe(recipe_data)
        if recipe:
            console.print(f"\n[bold green]✓[/bold green] Recipe '{recipe_name}' created successfully!")
            console.print(f"Recipe ID: {recipe.id}")
            
            # Show summary
            console.print(f"\n[bold blue]Recipe Summary:[/bold blue]")
            console.print(f"Name: {recipe.name}")
            console.print(f"Category: {recipe.category}")
            console.print(f"Difficulty: {recipe.difficulty}")
            console.print(f"Serving size: {recipe.serving_size_ml}ml")
            console.print(f"Ingredients: {len(ingredients)}")
            
            # Ask if they want to calculate cost
            if click.confirm("\nWould you like to calculate the cost for this recipe?"):
                console.print(f"\n[bold blue]Calculating cost...[/bold blue]")
                calculator = DrinkCostCalculator()
                calculation = calculator.calculate_drink_cost(recipe.id)
                if calculation:
                    console.print(f"[bold green]Cost: ${calculation.total_cost:.3f}[/bold green]")
                    console.print(f"Suggested price: ${calculation.suggested_selling_price:.2f}")
        else:
            console.print(f"[bold red]✗[/bold red] Failed to create recipe")
            
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Error creating recipe: {e}")
        logger.error(f"Error creating recipe: {e}")

def _parse_ingredient_input(input_str: str) -> Optional[Dict]:
    """Parse ingredient input string like '60ml Vodka' or '2 dash Bitters'"""
    import re
    
    # Common patterns
    patterns = [
        r'^(\d+(?:\.\d+)?)\s*(ml|oz|dash|splash|tsp|tbsp|cl|dl|l|whole|leaves|pinch)\s+(.+)$',
        r'^(\d+(?:\.\d+)?)\s*(.+)$'  # Fallback for just number + ingredient
    ]
    
    for pattern in patterns:
        match = re.match(pattern, input_str.strip(), re.IGNORECASE)
        if match:
            if len(match.groups()) == 3:
                amount, unit, ingredient = match.groups()
                return {
                    'amount': float(amount),
                    'unit': unit.lower(),
                    'ingredient_name': ingredient.strip()
                }
            elif len(match.groups()) == 2:
                amount, ingredient = match.groups()
                return {
                    'amount': float(amount),
                    'unit': 'ml',  # Default unit
                    'ingredient_name': ingredient.strip()
                }
    
    return None

@cli.command()
@click.argument('recipe_name')
def edit_recipe(recipe_name: str):
    """Edit an existing recipe"""
    console.print(f"[bold blue]Editing recipe: {recipe_name}[/bold blue]")
    
    try:
        recipe_service = RecipeService()
        recipe = recipe_service.find_recipe_by_name(recipe_name)
        
        if not recipe:
            console.print(f"[bold red]✗[/bold red] Recipe '{recipe_name}' not found")
            return
        
        console.print(f"[bold green]✓[/bold green] Found recipe: {recipe.name}")
        
        # Show current recipe details
        ingredients = recipe_service.get_recipe_ingredients(recipe.id)
        console.print(f"\n[bold yellow]Current Recipe:[/bold yellow]")
        console.print(f"Name: {recipe.name}")
        console.print(f"Category: {recipe.category}")
        console.print(f"Difficulty: {recipe.difficulty}")
        console.print(f"Serving size: {recipe.serving_size_ml}ml")
        console.print(f"Description: {recipe.description or 'None'}")
        console.print(f"Instructions: {recipe.instructions or 'None'}")
        console.print(f"Garnish: {recipe.garnish or 'None'}")
        console.print(f"Glass: {recipe.glass_type or 'None'}")
        
        console.print(f"\nIngredients:")
        for ing in ingredients:
            console.print(f"  - {ing.amount}{ing.unit} {ing.ingredient_name}")
        
        # Edit options
        console.print(f"\n[bold yellow]What would you like to edit?[/bold yellow]")
        console.print("1. Basic details (name, category, difficulty, etc.)")
        console.print("2. Instructions and description")
        console.print("3. Ingredients")
        console.print("4. Delete recipe")
        
        choice = click.prompt("Choice", type=click.Choice(['1', '2', '3', '4']))
        
        if choice == '1':
            _edit_basic_details(recipe_service, recipe)
        elif choice == '2':
            _edit_instructions(recipe_service, recipe)
        elif choice == '3':
            _edit_ingredients(recipe_service, recipe)
        elif choice == '4':
            if click.confirm(f"Are you sure you want to delete '{recipe.name}'?"):
                if recipe_service.delete_recipe(recipe.id):
                    console.print(f"[bold green]✓[/bold green] Recipe '{recipe.name}' deleted")
                else:
                    console.print(f"[bold red]✗[/bold red] Failed to delete recipe")
            
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Error editing recipe: {e}")
        logger.error(f"Error editing recipe: {e}")

def _edit_basic_details(recipe_service: RecipeService, recipe):
    """Edit basic recipe details"""
    console.print(f"\n[bold yellow]Editing Basic Details:[/bold yellow]")
    
    updates = {}
    
    new_name = click.prompt("Name", default=recipe.name)
    if new_name != recipe.name:
        updates['name'] = new_name
    
    new_category = click.prompt("Category", default=recipe.category or "Cocktail")
    if new_category != recipe.category:
        updates['category'] = new_category
    
    new_difficulty = click.prompt("Difficulty", default=recipe.difficulty or "Medium", 
                                type=click.Choice(['Easy', 'Medium', 'Hard']))
    if new_difficulty != recipe.difficulty:
        updates['difficulty'] = new_difficulty
    
    new_serving_size = click.prompt("Serving size (ml)", default=recipe.serving_size_ml or 120, type=float)
    if new_serving_size != recipe.serving_size_ml:
        updates['serving_size_ml'] = new_serving_size
    
    new_glass = click.prompt("Glass type", default=recipe.glass_type or "")
    if new_glass != recipe.glass_type:
        updates['glass_type'] = new_glass
    
    new_garnish = click.prompt("Garnish", default=recipe.garnish or "")
    if new_garnish != recipe.garnish:
        updates['garnish'] = new_garnish
    
    if updates:
        if recipe_service.update_recipe(recipe.id, updates):
            console.print(f"[bold green]✓[/bold green] Recipe updated successfully")
        else:
            console.print(f"[bold red]✗[/bold red] Failed to update recipe")
    else:
        console.print("No changes made")

def _edit_instructions(recipe_service: RecipeService, recipe):
    """Edit recipe instructions and description"""
    console.print(f"\n[bold yellow]Editing Instructions:[/bold yellow]")
    
    updates = {}
    
    console.print(f"Current description: {recipe.description or 'None'}")
    new_description = click.prompt("New description (or press Enter to keep current)", default="", show_default=False)
    if new_description:
        updates['description'] = new_description
    
    console.print(f"Current instructions: {recipe.instructions or 'None'}")
    new_instructions = click.prompt("New instructions (use \\n for line breaks, or press Enter to keep current)", default="", show_default=False)
    if new_instructions:
        updates['instructions'] = new_instructions.replace('\\n', '\n')
    
    if updates:
        if recipe_service.update_recipe(recipe.id, updates):
            console.print(f"[bold green]✓[/bold green] Instructions updated successfully")
        else:
            console.print(f"[bold red]✗[/bold red] Failed to update instructions")
    else:
        console.print("No changes made")

def _edit_ingredients(recipe_service: RecipeService, recipe):
    """Edit recipe ingredients"""
    ingredient_service = IngredientService()
    
    console.print(f"\n[bold yellow]Editing Ingredients for {recipe.name}:[/bold yellow]")
    
    while True:
        ingredients = recipe_service.get_recipe_ingredients(recipe.id)
        
        console.print(f"\nCurrent ingredients:")
        for i, ing in enumerate(ingredients, 1):
            console.print(f"{i}. {ing.amount}{ing.unit} {ing.ingredient_name} ({ing.ingredient_type})")
        
        console.print(f"\nOptions:")
        console.print("1. Add new ingredient")
        console.print("2. Modify existing ingredient")
        console.print("3. Remove ingredient")
        console.print("4. Done editing")
        
        choice = click.prompt("Choice", type=click.Choice(['1', '2', '3', '4']))
        
        if choice == '1':
            # Add new ingredient
            console.print("\nAdding new ingredient:")
            ingredient_input = click.prompt("Ingredient (e.g., '15ml Simple Syrup')")
            parsed = _parse_ingredient_input(ingredient_input)
            
            if parsed:
                # Get ingredient type and additional details
                ingredient_type = click.prompt("Type", 
                                             default="alcohol" if any(word in parsed['ingredient_name'].lower() 
                                                                    for word in ['vodka', 'gin', 'rum', 'whiskey', 'whisky', 'tequila', 'brandy', 'liqueur', 'wine', 'beer']) 
                                             else "mixer", 
                                             type=click.Choice(['alcohol', 'mixer', 'garnish']))
                
                if ingredient_type == 'alcohol':
                    # Get alcohol-specific details
                    categories = ['Spirits', 'Wine', 'Beer & Cider']
                    category_choice = click.prompt("Alcohol Category", default="Spirits", type=click.Choice(categories))
                    
                    subcategories = {
                        'Spirits': ['Vodka', 'Gin', 'Rum', 'Whisky', 'Tequila', 'Brandy', 'Liqueur'],
                        'Wine': ['Red Wine', 'White Wine', 'Sparkling Wine', 'Vermouth'],
                        'Beer & Cider': ['Beer', 'Cider']
                    }
                    
                    subcategory_choice = None
                    if category_choice in subcategories:
                        subcategory_choice = click.prompt("Subcategory", default="", type=click.Choice(subcategories[category_choice] + [""]), show_default=False) or None
                    
                    min_abv = click.prompt("Minimum ABV %", type=float, default=40.0) if category_choice == 'Spirits' else None
                    brand_pref = click.prompt("Preferred brand (optional)", default="", show_default=False) or None
                    
                    parsed.update({
                        'ingredient_type': ingredient_type,
                        'alcohol_category': category_choice,
                        'alcohol_subcategory': subcategory_choice,
                        'min_alcohol_percentage': min_abv,
                        'brand_preference': brand_pref
                    })
                else:
                    parsed['ingredient_type'] = ingredient_type
                
                # Add the ingredient
                new_ingredient = ingredient_service.add_ingredient_to_recipe(recipe.id, parsed)
                if new_ingredient:
                    console.print(f"[bold green]✓[/bold green] Added {parsed['ingredient_name']}")
                else:
                    console.print(f"[bold red]✗[/bold red] Failed to add ingredient")
            else:
                console.print(f"[bold red]✗[/bold red] Could not parse ingredient. Try format: '60ml Vodka'")
        
        elif choice == '2':
            # Modify existing ingredient
            if not ingredients:
                console.print("[bold red]No ingredients to modify[/bold red]")
                continue
                
            console.print("\nSelect ingredient to modify:")
            for i, ing in enumerate(ingredients, 1):
                console.print(f"{i}. {ing.amount}{ing.unit} {ing.ingredient_name}")
            
            try:
                idx = click.prompt("Ingredient number", type=int) - 1
                if 0 <= idx < len(ingredients):
                    ing = ingredients[idx]
                    
                    console.print(f"\nModifying: {ing.amount}{ing.unit} {ing.ingredient_name}")
                    console.print("What would you like to change?")
                    console.print("1. Amount")
                    console.print("2. Unit") 
                    console.print("3. Name")
                    console.print("4. Brand preference")
                    
                    mod_choice = click.prompt("Choice", type=click.Choice(['1', '2', '3', '4']))
                    updates = {}
                    
                    if mod_choice == '1':
                        new_amount = click.prompt("New amount", type=float, default=ing.amount)
                        updates['amount'] = new_amount
                    elif mod_choice == '2':
                        new_unit = click.prompt("New unit", default=ing.unit)
                        updates['unit'] = new_unit
                    elif mod_choice == '3':
                        new_name = click.prompt("New name", default=ing.ingredient_name)
                        updates['ingredient_name'] = new_name
                    elif mod_choice == '4':
                        new_brand = click.prompt("New brand preference", default=ing.brand_preference or "", show_default=False) or None
                        updates['brand_preference'] = new_brand
                    
                    if ingredient_service.update_ingredient(ing.id, updates):
                        console.print(f"[bold green]✓[/bold green] Updated ingredient")
                    else:
                        console.print(f"[bold red]✗[/bold red] Failed to update ingredient")
                else:
                    console.print("[bold red]Invalid ingredient number[/bold red]")
            except (ValueError, IndexError):
                console.print("[bold red]Invalid selection[/bold red]")
        
        elif choice == '3':
            # Remove ingredient
            if not ingredients:
                console.print("[bold red]No ingredients to remove[/bold red]")
                continue
                
            console.print("\nSelect ingredient to remove:")
            for i, ing in enumerate(ingredients, 1):
                console.print(f"{i}. {ing.amount}{ing.unit} {ing.ingredient_name}")
            
            try:
                idx = click.prompt("Ingredient number", type=int) - 1
                if 0 <= idx < len(ingredients):
                    ing = ingredients[idx]
                    
                    if click.confirm(f"Remove {ing.ingredient_name}?"):
                        if ingredient_service.remove_ingredient(ing.id):
                            console.print(f"[bold green]✓[/bold green] Removed {ing.ingredient_name}")
                        else:
                            console.print(f"[bold red]✗[/bold red] Failed to remove ingredient")
                else:
                    console.print("[bold red]Invalid ingredient number[/bold red]")
            except (ValueError, IndexError):
                console.print("[bold red]Invalid selection[/bold red]")
        
        elif choice == '4':
            # Done editing
            console.print(f"[bold green]✓[/bold green] Finished editing ingredients for {recipe.name}")
            break

@cli.command()
def load_recipes():
    """Load default cocktail recipes into the database"""
    console.print("[bold blue]Loading default recipes...[/bold blue]")
    
    try:
        recipe_service = RecipeService()
        count = recipe_service.load_default_recipes()
        console.print(f"[bold green]✓[/bold green] Loaded {count} new recipes")
        
        # Show loaded recipes
        recipes = recipe_service.get_all_recipes()
        if recipes:
            table = Table(title="Available Recipes")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="white")
            table.add_column("Category", style="green")
            table.add_column("Difficulty", style="yellow")
            table.add_column("Ingredients", style="blue")
            
            for recipe in recipes:
                ingredients = recipe_service.get_recipe_ingredients(recipe.id)
                ingredient_count = len(ingredients)
                table.add_row(
                    str(recipe.id),
                    recipe.name,
                    recipe.category or "N/A",
                    recipe.difficulty or "N/A",
                    str(ingredient_count)
                )
            
            console.print(table)
            
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to load recipes: {e}")
        logger.error(f"Failed to load recipes: {e}")

@cli.command()
@click.argument('drink_name')
@click.option('--cost-option', '-c', default='mid_range', 
              type=click.Choice(['cheapest', 'mid_range', 'premium']),
              help='Cost calculation option')
@click.option('--city', default='St. Catharines', help='City for store availability')
def calculate_drink_cost(drink_name: str, cost_option: str, city: str):
    """Calculate the cost to make a specific drink"""
    console.print(f"[bold blue]Calculating cost for: {drink_name}[/bold blue]")
    
    try:
        # Find the recipe
        recipe_service = RecipeService()
        recipe = recipe_service.find_recipe_by_name(drink_name)
        
        if not recipe:
            console.print(f"[bold red]✗[/bold red] Recipe '{drink_name}' not found")
            
            # Show available recipes
            recipes = recipe_service.get_all_recipes()
            if recipes:
                console.print("\n[bold yellow]Available recipes:[/bold yellow]")
                for r in recipes:
                    console.print(f"  - {r.name}")
            return
        
        console.print(f"[bold green]✓[/bold green] Found recipe: {recipe.name}")
        console.print(f"Category: {recipe.category}")
        console.print(f"Serving size: {recipe.serving_size_ml}ml")
        
        # Show ingredients
        ingredients = recipe_service.get_recipe_ingredients(recipe.id)
        if ingredients:
            console.print("\n[bold yellow]Ingredients:[/bold yellow]")
            for ingredient in ingredients:
                console.print(f"  - {ingredient.amount}{ingredient.unit} {ingredient.ingredient_name}")
        
        # Calculate cost
        console.print(f"\n[bold blue]Calculating costs using {cost_option} options...[/bold blue]")
        
        calculator = DrinkCostCalculator(city=city)
        calculation = calculator.calculate_drink_cost(recipe.id, cost_option)
        
        if not calculation:
            console.print(f"[bold red]✗[/bold red] Failed to calculate cost")
            return
        
        # Display results
        console.print(f"\n[bold green]✓[/bold green] Cost calculation complete!")
        
        # Main cost table
        cost_table = Table(title=f"{recipe.name} Cost Breakdown")
        cost_table.add_column("Metric", style="cyan")
        cost_table.add_column("Value", style="white")
        
        cost_table.add_row("Total Ingredient Cost", f"${calculation.total_cost:.3f}")
        cost_table.add_row("Alcohol Cost", f"${calculation.total_alcohol_cost:.3f}")
        cost_table.add_row("Mixer Cost", f"${calculation.total_mixer_cost:.3f}")
        cost_table.add_row("Cost per ml", f"${calculation.cost_per_ml:.4f}")
        cost_table.add_row("Suggested Selling Price", f"${calculation.suggested_selling_price:.2f}")
        cost_table.add_row("Profit Margin", f"${calculation.suggested_selling_price - calculation.total_cost:.2f}")
        cost_table.add_row("Markup Percentage", f"{calculation.markup_suggested:.0f}%")
        
        console.print(cost_table)
        
        # Availability info
        if not calculation.all_ingredients_available:
            missing = json.loads(calculation.missing_ingredients)
            console.print(f"\n[bold red]⚠ Missing ingredients:[/bold red] {', '.join(missing)}")
        else:
            console.print(f"\n[bold green]✓ All ingredients available in {city}[/bold green]")
        
        # Sale information
        sale_ingredients = json.loads(calculation.ingredients_on_sale)
        if sale_ingredients:
            console.print(f"\n[bold yellow]🎉 Items on sale:[/bold yellow]")
            for item in sale_ingredients:
                console.print(f"  - {item['ingredient']}: {item['product']} (Save ${item['savings']:.3f})")
            console.print(f"Total savings: ${calculation.total_sale_savings:.3f}")
        
        # Cost comparison
        if calculation.lowest_cost_option and calculation.premium_cost_option:
            console.print(f"\n[bold blue]Cost Options:[/bold blue]")
            console.print(f"  Cheapest: ${calculation.lowest_cost_option:.3f}")
            console.print(f"  Current ({cost_option}): ${calculation.total_cost:.3f}")
            console.print(f"  Premium: ${calculation.premium_cost_option:.3f}")
        
        # Get detailed breakdown
        breakdown = calculator.get_cost_breakdown(calculation.id)
        if breakdown['ingredients']:
            ingredient_table = Table(title="Ingredient Details")
            ingredient_table.add_column("Ingredient", style="cyan")
            ingredient_table.add_column("Brand", style="green")
            ingredient_table.add_column("Amount", style="yellow")
            ingredient_table.add_column("Cost", style="white")
            ingredient_table.add_column("Bottle Price", style="magenta")
            ingredient_table.add_column("Bottle Size", style="dim")
            ingredient_table.add_column("In Stock", style="blue")
            ingredient_table.add_column("Sale", style="red")
            
            for ingredient in breakdown['ingredients']:
                in_stock = "✓" if ingredient['in_stock'] else "✗"
                on_sale = "🏷️" if ingredient.get('sale_savings') else ""
                
                ingredient_table.add_row(
                    ingredient['name'][:25] + "..." if len(ingredient['name']) > 25 else ingredient['name'],
                    ingredient['brand'] or "N/A",
                    ingredient['amount_needed'],
                    ingredient['cost'],
                    ingredient.get('bottle_price', 'N/A'),
                    ingredient.get('bottle_size', 'N/A'),
                    in_stock,
                    on_sale
                )
            
            console.print(ingredient_table)
        
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to calculate drink cost: {e}")
        logger.error(f"Failed to calculate drink cost: {e}")

@cli.command()
@click.option('--limit', '-l', default=10, help='Number of recipes to show')
def list_recipes(limit: int):
    """List available drink recipes"""
    try:
        recipe_service = RecipeService()
        recipes = recipe_service.get_all_recipes()
        
        if not recipes:
            console.print("[bold yellow]No recipes found. Use 'load-recipes' to add default recipes.[/bold yellow]")
            return
        
        table = Table(title="Available Drink Recipes")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="white")
        table.add_column("Category", style="green")
        table.add_column("Difficulty", style="yellow")
        table.add_column("Prep Time", style="blue")
        table.add_column("Serving Size", style="magenta")
        
        for recipe in recipes[:limit]:
            table.add_row(
                str(recipe.id),
                recipe.name,
                recipe.category or "N/A",
                recipe.difficulty or "N/A",
                f"{recipe.prep_time_minutes}min" if recipe.prep_time_minutes else "N/A",
                f"{recipe.serving_size_ml}ml" if recipe.serving_size_ml else "N/A"
            )
        
        console.print(table)
        
        if len(recipes) > limit:
            console.print(f"\n[bold blue]Showing {limit} of {len(recipes)} recipes. Use --limit to see more.[/bold blue]")
            
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to list recipes: {e}")
        logger.error(f"Failed to list recipes: {e}")

@cli.command()
@click.argument('search_term')
def search_recipes(search_term: str):
    """Search for recipes by name or category"""
    try:
        recipe_service = RecipeService()
        recipes = recipe_service.search_recipes(search_term)
        
        if not recipes:
            console.print(f"[bold yellow]No recipes found matching '{search_term}'[/bold yellow]")
            return
        
        console.print(f"[bold green]Found {len(recipes)} recipe(s) matching '{search_term}':[/bold green]")
        
        for recipe in recipes:
            console.print(f"\n[bold white]{recipe.name}[/bold white]")
            console.print(f"  Category: {recipe.category}")
            console.print(f"  Description: {recipe.description}")
            
            ingredients = recipe_service.get_recipe_ingredients(recipe.id)
            if ingredients:
                console.print("  Ingredients:")
                for ingredient in ingredients:
                    console.print(f"    - {ingredient.amount}{ingredient.unit} {ingredient.ingredient_name}")
            
    except Exception as e:
        console.print(f"[bold red]✗[/bold red] Failed to search recipes: {e}")
        logger.error(f"Failed to search recipes: {e}")

if __name__ == '__main__':
    cli()