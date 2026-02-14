# Kalshi Best Bets

A fully automated betting bot that analyzes NCAA basketball markets on Kalshi using BartTorvik probabilities to identify positive expected value (EV) betting opportunities.

## 🎯 What It Does

Every day, the bot:

1. **Scrapes BartTorvik data** using Selenium (headless Chrome) for:
   - Today's upcoming NCAA games (with win probabilities)
   - TourneyCast "IN %" (make NCAA tournament probabilities)  
   - ConCast conference title probabilities (SOLE and SHARE) for 9 major conferences

2. **Pulls Kalshi market data** for matching markets via their API

3. **Calculates expected value** and prints a ranked list of the best bets with the largest positive edge

4. **Saves results** to CSV + JSON files for analysis

## 🚀 Quick Start (Copy-Paste Instructions)

### Prerequisites

- Docker and Docker Compose (recommended) OR Python 3.11+ with Chrome/Chromium
- Git

### Option 1: Docker (Easiest)

```bash
# 1. Clone the repository
git clone <repository-url>
cd kalshi-best-bets

# 2. Build and run
make docker-build
make docker-run

# 3. Run daily with scheduler
docker-compose up kalshi-bets-scheduler
```

### Option 2: Local Python

```bash
# 1. Clone and install dependencies
git clone <repository-url>
cd kalshi-best-bets
make install

# 2. Run the bot
make run

# 3. Test first (recommended)
make dry-run
```

### Option 3: Manual Setup

```bash
# 1. Install Python dependencies
pip3 install -r requirements.txt

# 2. Run the bot
python3 src/main.py --help
python3 src/main.py --dry-run
```

## ⚙️ Configuration

Edit `config/config.yaml` for settings:

```yaml
# EV calculation settings
ev:
  min_ev: 0.02  # Minimum EV to include
  share_factor: 0.5  # Expected payout for shared championships
  top_bets: 20  # Number of top bets to display

# Add Kalshi API credentials (optional for public data)
kalshi:
  api_key: "your_api_key_here"
  api_secret: "your_api_secret_here"
```

## 📊 Output

The bot displays a formatted table:

```
🏀 TOP 20 KALSHI BEST BETS 🏀
================================================================================
Market Type        | League/Conf    | Description                               | Model Prob/Exp Payout | Yes Price | EV
--------------------+----------------+-------------------------------------------+-----------------------+-----------+-----
Make Tournament     | March Madness  | Duke to Make Tournament                   | 0.750                 | $0.65     | $0.100
Conference Champion | ACC            | Duke to Win ACC                           | 0.450                 | $0.35     | $0.100
...
```

Results are saved to `out/YYYY-MM-DD/`:
- `best_bets.csv` - Detailed results
- `best_bets.json` - Full data in JSON format  
- `unmatched_teams.csv` - Teams that couldn't be matched
- `unmatched_contracts.csv` - Contracts that couldn't be matched
- `log.txt` - Detailed execution log

## 🏀 Market Types Supported

### 1. Make Tournament (Round of 64 Qualifiers)
- **Market**: "Men's March Madness Round of 64 Qualifiers"
- **Model**: TourneyCast IN% probabilities
- **EV**: `model_prob - market_price`

### 2. Conference Champions (9 Major Conferences)
- **Markets**: "Big Ten Regular Season Champion", "SEC Regular Season Champion", etc.
- **Model**: ConCast SOLE and SHARE probabilities
- **EV**: `(p_sole * 1.0 + p_share * share_factor) - market_price`

### 3. Daily Games (Optional)
- **Markets**: NCAA game winner markets
- **Model**: BartTorvik win probabilities
- **EV**: `p_win - market_price`

## 🛠️ Command Line Options

```bash
# Basic usage
python3 src/main.py

# Specify date
python3 src/main.py --date 2024-03-15

# Custom thresholds
python3 src/main.py --min-ev 0.03 --share-factor 0.4 --top 25

# Save screenshots for debugging
python3 src/main.py --screenshots

# Dry run (no trading)
python3 src/main.py --dry-run
```

## 🐳 Docker Deployment

### Build and Run
```bash
# Build the image
make docker-build

# Run once
make docker-run

# Run with scheduler (daily at 10:30 AM America/Chicago)
docker-compose up kalshi-bets-scheduler
```

### Docker Compose Services
- `kalshi-bets`: Main bot service
- `kalshi-bets-scheduler`: Automated daily runner

## ⏰ Daily Scheduling

### Option 1: Docker Compose (Recommended)
```bash
docker-compose up -d kalshi-bets-scheduler
```

### Option 2: Cron
```bash
make schedule
```

### Option 3: Systemd Timer
```bash
make install-systemd-timer
```

## 🧪 Testing

```bash
# Run unit tests
make test

# Test with coverage
make test-cov

# Test the bot without API calls
python3 src/main.py --dry-run --screenshots
```

## 📁 Project Structure

```
kalshi-best-bets/
├── src/
│   ├── main.py              # CLI entry point
│   ├── config.py            # Configuration management
│   ├── browser.py           # Selenium browser client
│   ├── matcher.py           # Team name matching
│   ├── ev.py                # EV calculation
│   ├── output.py            # Report generation
│   ├── scrapers/            # BartTorvik scrapers
│   │   ├── schedule_scraper.py
│   │   ├── tourneycast_scraper.py
│   │   └── concast_scraper.py
│   └── kalshi/              # Kalshi API client
│       └── kalshi_client.py
├── config/
│   ├── config.yaml          # Main configuration
│   └── conference_map.yaml  # Conference name mappings
├── tests/                   # Unit tests
├── out/                     # Output directory (auto-created)
├── Dockerfile               # Docker configuration
├── docker-compose.yml       # Docker Compose setup
├── Makefile                 # Convenience commands
└── requirements.txt         # Python dependencies
```

## 🔧 Troubleshooting

### Chrome/ChromeDriver Issues
```bash
# If you get Chrome version mismatch, try:
python3 src/main.py --screenshots  # This will show the error

# Or use Docker which includes Chrome:
make docker-build && make docker-run
```

### No Markets Found
```bash
# Check if markets exist for today
python3 src/main.py --dry-run --verbose

# Try a different date
python3 src/main.py --date 2024-03-15
```

### Team Matching Issues
Check `out/YYYY-MM-DD/unmatched_teams.csv` and `unmatched_contracts.csv` for debugging.

## 🤖 How It Works

### Data Collection
1. **Selenium Scraping**: Uses undetected Chrome to scrape BartTorvik
2. **Kalshi API**: Public endpoints for market data and prices
3. **Team Matching**: Fuzzy matching with rapidfuzz for robust team name matching

### EV Calculation
- **Make Tournament**: Simple binary EV calculation
- **Conference Champions**: Handles sole/shared championship payouts
- **Game Winners**: Standard win probability EV

### Safety Features
- **No trading by default**: Analytics only
- **Configurable thresholds**: Adjustable EV and edge filters
- **Comprehensive logging**: Full audit trail
- **Error handling**: Graceful failure modes

## 📈 Performance

- **Runtime**: ~2-5 minutes for full analysis
- **Memory**: < 200MB typical usage
- **Chrome**: Headless mode for performance
- **Accuracy**: Team matching > 95% with fuzzy matching

## ⚠️ Important Notes

- **Analytics Only**: This bot does NOT place trades by default
- **Educational Purpose**: Use at your own risk
- **Market Availability**: Kalshi markets may not exist for all games
- **Chrome Required**: Selenium needs Chrome/Chromium browser

## 🆘 Support

If you encounter issues:

1. Check the logs in `out/YYYY-MM-DD/log.txt`
2. Run with `--verbose` for detailed output
3. Use `--screenshots` to debug scraping issues
4. Try Docker if local setup fails

---

**Happy betting! 🏀💰**
