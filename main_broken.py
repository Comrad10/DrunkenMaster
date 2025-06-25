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
from src.crawlers import CoveoAPIInvestigator, CategoryCrawler, ProductCrawler
from src.storage import ProductStorage
from src.utils import logger

console = Console()

@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--config', '-c', help='Path to config file')
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
async def investigate():
    """Investigate Coveo API endpoints and structure"""
    console.print("[bold blue]Investigating LCBO website structure...[/bold blue]")
    
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

@cli.command()
@click.option('--category', '-c', default='wine', help='Category to crawl (wine, beer-cider, spirits, etc.)')
@click.option('--max-pages', '-p', default=10, help='Maximum pages to crawl')
@click.option('--save', '-s', is_flag=True, help='Save products to database')
async def crawl_category(category: str, max_pages: int, save: bool):
    """Crawl products from a specific category"""
    console.print(f"[bold blue]Crawling category: {category}[/bold blue]")
    
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

@cli.command()
@click.option('--all-categories', '-a', is_flag=True, help='Crawl all categories')
@click.option('--categories', '-c', multiple=True, help='Specific categories to crawl')
@click.option('--max-pages', '-p', default=10, help='Maximum pages per category')
async def crawl_all(all_categories: bool, categories: List[str], max_pages: int):
    """Crawl all categories or specified categories"""
    if all_categories:
        target_categories = config.CATEGORIES
    elif categories:
        target_categories = list(categories)
    else:
        target_categories = config.CATEGORIES
    
    console.print(f"[bold blue]Crawling categories: {', '.join(target_categories)}[/bold blue]")
    
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

@cli.command()
@click.option('--limit', '-l', default=20, help='Limit number of products to show')
@click.option('--category', '-c', help='Filter by category')
def list_products(limit: int, category: Optional[str]):
    """List products from the database"""
    try:
        storage = ProductStorage()
        
        if category:
            products = storage.get_products_by_category(category, limit)
        else:
            products = storage.get_all_products(limit)
        
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
        
        with storage.get_session() as session:
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
        storage = ProductStorage()
        products = storage.get_all_products()
        
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

def run_async_command(coro):
    """Helper to run async commands"""
    return asyncio.run(coro)

# Update async command decorators
investigate = cli.command()(lambda: run_async_command(investigate()))
crawl_category = cli.command()(lambda category, max_pages, save: run_async_command(crawl_category(category, max_pages, save)))
crawl_all = cli.command()(lambda all_categories, categories, max_pages: run_async_command(crawl_all(all_categories, categories, max_pages)))

if __name__ == '__main__':
    cli()