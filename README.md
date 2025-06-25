# LCBO Crawler & Bar Cost Calculator

A comprehensive tool for collecting LCBO product information and calculating cocktail costs for bar management.

## Features

### Web Crawling
- 🔍 **Respectful Crawling**: Built-in rate limiting and respectful request patterns
- 📊 **Comprehensive Data**: Collects product details, pricing, and inventory information
- 🗄️ **Database Storage**: SQLite database with price history tracking
- 🔄 **API Investigation**: Reverse-engineers Coveo search API endpoints
- 📍 **Store Locations**: Tracks product availability at specific LCBO stores
- 🛡️ **Error Handling**: Robust retry logic and circuit breaker patterns

### Recipe & Cost Management
- 🍸 **Recipe Database**: 47+ popular cocktail recipes with full ingredient lists
- 💰 **Cost Calculator**: Calculates exact costs to make each cocktail
- 🏪 **Store Integration**: Shows which stores have ingredients in stock
- 🏷️ **Sale Detection**: Identifies products on sale and calculates savings
- 📊 **Detailed Breakdown**: Shows bottle costs, amounts used, and profit margins
- ✏️ **Recipe Editor**: Create and modify cocktail recipes with ingredient management
- 🎯 **Product Matching**: Intelligent matching of recipe ingredients to LCBO products

## Installation

1. **Clone and navigate to the directory:**
   ```bash
   cd lcbo_crawler
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright browsers:**
   ```bash
   playwright install chromium
   ```

4. **Initialize the database:**
   ```bash
   python main.py init
   ```

## Usage

### Setup Commands

**Initialize Database:**
```bash
python main.py init
```

**Load Default Recipes:**
```bash
python main.py load-recipes
```

**Find LCBO Stores (St. Catharines):**
```bash
python main.py find-stores
```

### Web Crawling Commands

**Investigate API Structure:**
```bash
python main.py investigate
```

**Crawl a Specific Category:**
```bash
python main.py crawl-category --category wine --save
```

**Crawl All Categories:**
```bash
python main.py crawl-all --all-categories
```

**List Products:**
```bash
python main.py list-products --limit 10 --category wine
```

### Recipe & Cost Commands

**Calculate Drink Cost:**
```bash
python main.py calculate-drink-cost "Old Fashioned" --cost-option mid_range
```

**List Available Recipes:**
```bash
python main.py list-recipes --limit 20
```

**Create New Recipe:**
```bash
python main.py create-recipe "My Custom Cocktail" --category Cocktail
```

**Edit Existing Recipe:**
```bash
python main.py edit-recipe "Old Fashioned"
```

### Data Management Commands

**View Statistics:**
```bash
python main.py stats
```

**Export Data:**
```bash
python main.py export --output my_products.json
```

### Available Categories

- `wine`
- `beer-cider`
- `spirits`
- `coolers`
- `non-alcoholic`

### Configuration

Copy `.env.example` to `.env` and customize settings:

```bash
cp .env.example .env
```

Key settings:
- `MIN_REQUEST_DELAY`: Minimum delay between requests (default: 2 seconds)
- `MAX_REQUEST_DELAY`: Maximum delay between requests (default: 5 seconds)
- `AVOID_HOURS_START`: Start of restricted crawling hours (default: 17 - 5 PM)
- `AVOID_HOURS_END`: End of restricted crawling hours (default: 20 - 8 PM)

## Data Collected

For each product, the crawler collects:

### Basic Information
- LCBO ID
- Product name
- Brand
- Category and subcategory
- Description

### Pricing
- Current price
- Regular price (if on sale)
- Price history over time

### Product Details
- Volume (in mL)
- Alcohol percentage
- Country of origin
- Region/appellation
- Style/varietal

### Additional Data
- Product images
- Product URLs
- Inventory status
- Last updated timestamps

## Database Schema

The crawler uses SQLite with three main tables:

- **products**: Main product information
- **price_history**: Historical pricing data
- **inventory**: Stock and availability information

## Respectful Crawling Practices

This crawler follows best practices for web scraping:

- **Rate Limiting**: 2-5 second delays between requests
- **Time Restrictions**: Avoids peak hours (5-8 PM by default)
- **Single Connection**: No concurrent requests
- **Error Handling**: Backs off on errors and respects server responses
- **Personal Use Only**: Data is stored locally and not redistributed

## Project Structure

```
lcbo_crawler/
├── src/
│   ├── crawlers/           # Web crawling logic
│   ├── parsers/            # Data extraction and parsing
│   ├── models/             # Database models
│   ├── storage/            # Data storage layer
│   ├── utils/              # Utilities (logging, rate limiting, etc.)
│   └── config.py           # Configuration management
├── data/                   # Data files and database
├── logs/                   # Log files
├── tests/                  # Test files
├── main.py                 # CLI interface
├── requirements.txt        # Dependencies
└── README.md              # This file
```

## Development

### Running Tests
```bash
pytest tests/
```

### Code Formatting
```bash
black src/
flake8 src/
```

### Adding New Features

1. **New Crawlers**: Add to `src/crawlers/`
2. **New Parsers**: Add to `src/parsers/`
3. **Database Changes**: Update models in `src/models/`
4. **CLI Commands**: Add to `main.py`

## Monitoring

The crawler provides detailed logging and monitoring:

- **Logs**: Saved to `logs/crawler.log` with rotation
- **Progress**: Real-time progress indicators
- **Statistics**: Database statistics and crawl metrics
- **Error Tracking**: Comprehensive error logging and handling

## Troubleshooting

### Common Issues

**"Database is locked" Error:**
- Ensure no other instances are running
- Check file permissions on the database

**"Navigation timeout" Error:**
- Check internet connection
- Verify LCBO website is accessible
- Increase timeout in configuration

**"No products found" Error:**
- Run API investigation first: `python main.py investigate`
- Check if website structure has changed
- Verify category names are correct

### Debug Mode

Enable verbose logging:
```bash
python main.py --verbose [command]
```

## Legal Considerations

This tool is designed for personal use only:

- ✅ Personal data collection and analysis
- ✅ Price tracking for personal purchases
- ✅ Inventory monitoring for personal use
- ❌ Commercial use or redistribution
- ❌ Overwhelming server resources
- ❌ Violating terms of service

## License

This project is for educational and personal use only. Please respect LCBO's terms of service and use responsibly.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the logs in `logs/crawler.log`
3. Ensure you're following respectful crawling practices

---

**Disclaimer**: This tool is for personal use only. Users are responsible for complying with all applicable terms of service and legal requirements.