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

## How It Works

### System Architecture

The DrunkenMaster system is built with a modular architecture that separates concerns into distinct layers:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   CLI Interface │    │  Recipe Engine  │    │  Web Crawler    │
│    (main.py)    │◄──►│   (services/)   │◄──►│  (crawlers/)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Database     │    │ Product Matcher │    │   Data Parser   │
│   (models/)     │◄──►│   Algorithm     │◄──►│   (parsers/)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Core Components

#### 1. Web Crawler (`src/crawlers/`)
**How it works:**
- **Reverse Engineering**: Analyzes LCBO's website to discover their internal Coveo search API
- **Respectful Crawling**: Uses 2-5 second delays and avoids peak hours (5-8 PM)
- **Playwright Automation**: Controls a headless Chrome browser to handle JavaScript-rendered content
- **Error Handling**: Implements retry logic and circuit breakers for network failures

**Key Files:**
- `api_investigator.py` - Discovers API endpoints and parameters
- `product_crawler.py` - Extracts product data from search results
- `store_locator.py` - Finds store locations and IDs
- `store_inventory_crawler.py` - Checks product availability at specific stores

#### 2. Recipe Engine (`src/services/`)
**How it works:**
- **Recipe Database**: Stores 47+ cocktail recipes with detailed ingredient specifications
- **Product Matching**: Uses a scoring algorithm to match recipe ingredients to LCBO products
- **Cost Calculation**: Computes exact costs including bottle prices, amounts used, and profit margins
- **Sale Detection**: Identifies products on sale and calculates potential savings

**Algorithm Details:**
```python
# Product Matching Score Calculation
score = 0
+ exact_name_match * 100      # Highest priority
+ brand_preference * 50       # User specified brand
+ alcohol_type_match * 30     # Vodka matches "vodka" products
+ category_match * 20         # Spirits category match
+ ABV_sufficient * 10         # Meets minimum alcohol percentage
- ABV_too_low * 20           # Penalty for insufficient alcohol
+ keyword_overlap * 5         # Individual word matches
+ price_range_bonus * 5       # Prefer mid-range products
```

#### 3. Database Schema (`src/models/`)
**Core Tables:**
- **Products**: LCBO product data with pricing and inventory
- **Recipes**: Cocktail recipes with metadata
- **RecipeIngredients**: Detailed ingredient specifications
- **Stores**: LCBO store locations and information
- **StoreInventory**: Product availability by store
- **DrinkCostCalculations**: Historical cost calculations
- **IngredientCosts**: Detailed cost breakdowns

#### 4. Data Flow

```
1. User Request: "Calculate Old Fashioned cost"
         ↓
2. Recipe Lookup: Find "Old Fashioned" in database
         ↓
3. Ingredient Analysis: Extract required ingredients
   - 60ml Bourbon Whiskey
   - 10ml Simple Syrup  
   - 2 dash Angostura Bitters
         ↓
4. Product Matching: For each alcohol ingredient
   - Search LCBO database for matching products
   - Score candidates using matching algorithm
   - Select best option based on cost preference
         ↓
5. Cost Calculation:
   - Alcohol: price_per_ml × amount_needed
   - Mixers: predefined cost estimates
   - Total: sum all ingredients
         ↓
6. Enhanced Display:
   - Cost breakdown with bottle prices
   - Store availability
   - Sale detection
   - Profit margin calculation (300% markup)
```

### Technical Implementation

#### Web Scraping Strategy
**Challenge**: LCBO uses a modern React SPA with dynamic content loading
**Solution**: 
- Reverse-engineered their Coveo search API endpoints
- Bypassed the UI by making direct API calls
- Handles pagination and filtering automatically

#### Product Matching Intelligence
**Challenge**: Recipe ingredients like "Bourbon Whiskey" need to match specific LCBO products
**Solution**:
- Multi-tier scoring system with exact matches, brand preferences, and keyword analysis
- Handles variations ("whiskey" vs "whisky", "triple sec" vs "orange liqueur")
- Provides price range options (cheapest, mid-range, premium)

#### Store Integration
**Challenge**: Track inventory across multiple store locations
**Solution**:
- Automated store discovery for St. Catharines area (found 5 stores)
- Real-time availability checking through LCBO's inventory API
- Geographic filtering for relevant locations

### Performance Optimizations

1. **Database Indexing**: Strategic indexes on frequently queried fields
2. **Session Management**: Proper SQLAlchemy session handling with connection pooling
3. **Caching**: Stores API responses to reduce redundant requests
4. **Batch Processing**: Groups multiple operations for better performance
5. **Rate Limiting**: Prevents overwhelming LCBO's servers

### Error Handling & Reliability

- **Circuit Breaker Pattern**: Stops making requests if error rate exceeds threshold
- **Exponential Backoff**: Gradually increases delay between retry attempts  
- **Session Recovery**: Handles database connection issues gracefully
- **Graceful Degradation**: System continues working even if some components fail

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

## Development Philosophy

This project was built using an iterative, user-driven approach called "vibe coding" - starting with curiosity and letting requirements emerge naturally through experimentation and feedback. 

**📖 Read the full development story**: [DEVELOPMENT_PROCESS.md](DEVELOPMENT_PROCESS.md)

Learn how this project evolved from "I wonder about drink costs" to a complete bar management system, and how you can apply the same approach to your own projects.

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