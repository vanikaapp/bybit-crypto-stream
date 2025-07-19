# Crypto Bot - Bybit V5 API Integration

A Python cryptocurrency bot that connects to Bybit V5 API to fetch historical OHLC data and stream live market data in real-time.

## Features

- ✅ Connects to Bybit V5 API
- ✅ Fetches 48 hours of 1-minute OHLC historical data
- ✅ Streams live trade data via WebSocket
- ✅ Builds real-time OHLC candles from live trades
- ✅ Continuously updates historical dataset with new candles
- ✅ Data Persistence - Automatically saves historical data to CSV files in `/data` folder
- ✅ Thread-safe data handling
- ✅ Comprehensive logging
- ✅ Mainnet live data streaming

## Installation

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Quick Start

### Basic Usage

### Run the Main Bot
```bash
python crypto_bot.py
```

### Custom Usage in Your Code
```python
from crypto_bot import CryptoBot

# Create bot instance
bot = CryptoBot(symbol="BTCUSDT", data_dir="data")

# Run the bot
bot.run()
```

### Different Trading Pairs
```python
from crypto_bot import CryptoBot

# Use different trading pair
bot = CryptoBot(symbol="ETHUSDT")
bot.run()
```

This will:
1. Fetch 48 hours of historical BTCUSDT data
2. Start live streaming
3. Automatically save data to `/data` folder
4. Display real-time updates and statistics

## How It Works

### 1. Historical Data Fetching
- Downloads 48 hours of 1-minute OHLC data from Bybit V5 API
- Stores data in pandas DataFrame for efficient processing
- Automatically saves to CSV file in `/data` folder
- Provides foundation dataset for analysis

### 2. Live Data Streaming
- Connects to Bybit V5 WebSocket (`wss://stream.bybit.com/v5/public/spot`)
- Subscribes to real-time trade data for specified symbol
- Processes incoming trades in real-time

### 3. Real-time OHLC Building
- Groups trades by 1-minute intervals
- Calculates Open, High, Low, Close, Volume, and Turnover
- Automatically finalizes completed candles

### 4. Data Management & Persistence
- Thread-safe data operations using locks
- Continuous integration of live data with historical dataset
- Automatic CSV file saving every 10 new candles
- Final data save when bot stops
- Real-time statistics and monitoring

## Configuration

### Symbol Selection
```python
bot = CryptoBot(symbol="ETHUSDT")
```

### Historical Data Period
```python
bot.fetch_historical_data(interval="1", hours=24)  # 24 hours instead of 48
```

### Environment Variables
Create a `.env` file (optional):
```
DEFAULT_SYMBOL=BTCUSDT
HISTORICAL_HOURS=48
LOG_LEVEL=INFO
```

## API Reference

### CryptoBot Class

#### Constructor
```python
CryptoBot(
    symbol="BTCUSDT",  # Trading pair symbol
    data_dir="data"    # Directory to save CSV files (optional)
)
```

#### Methods

- `fetch_historical_data(interval="1", hours=48)` - Fetch historical OHLC data
- `start_live_stream()` - Start WebSocket live data stream
- `stop_live_stream()` - Stop live data stream
- `get_latest_data(rows=10)` - Get latest OHLC candles
- `get_current_candle_info()` - Get current incomplete candle info
- `run()` - Main execution method

## Data Structure

### Historical Data DataFrame
```
Columns: ['timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover']
Types: [datetime64, float64, float64, float64, float64, float64, float64]
```

### Live Trade Data
```python
{
    'timestamp': 1640995200000,  # Unix timestamp in milliseconds
    'price': 47500.50,           # Trade price
    'volume': 0.001              # Trade volume
}
```

### Current Candle Structure
```python
{
    'timestamp': datetime_object,
    'open': 47500.00,
    'high': 47600.00,
    'low': 47450.00,
    'close': 47580.00,
    'volume': 1.5,
    'turnover': 71370.00,
    'trade_count': 25
}
```

## Data Files

### CSV File Format
Historical data is automatically saved to CSV files in the `/data` folder with the following naming convention:
```
{SYMBOL}_historical_{YYYYMMDD}.csv
```

Example: `BTCUSDT_historical_20250718.csv`

### CSV Structure
```csv
timestamp,open,high,low,close,volume,turnover
2025-07-18 09:37:00,118696.0,118746.8,118696.0,118744.5,2.048211,243168.4063372
2025-07-18 09:38:00,118744.5,118817.0,118739.5,118739.5,5.384754,639572.9426756
...
```

### Data Persistence Features
- **Automatic Saving**: Historical data saved immediately after fetching
- **Incremental Updates**: New candles saved every 10 completed candles
- **Final Save**: All data saved when bot stops
- **Daily Files**: Separate CSV file created for each day
- **Data Recovery**: Can load existing CSV files on restart

## Logging

The bot provides comprehensive logging:
- Historical data fetch progress
- WebSocket connection status
- Live trade processing
- Candle completion notifications
- Error handling and debugging

## Safety Features

- **Read-only data collection** - No trading functionality
- **Error handling** - Graceful error recovery
- **Thread safety** - Concurrent data access protection
- **Resource limits** - Memory-efficient data storage
- **SSL security** - Secure WebSocket connections

## Troubleshooting

### Common Issues

1. **Connection Errors**
   - Check internet connection
   - Verify Bybit API status
   - Check firewall settings

2. **No Live Data**
   - Ensure WebSocket connection is established
   - Check symbol validity
   - Verify market hours (crypto markets are 24/7)

3. **Memory Issues**
   - Reduce historical data period
   - Implement data cleanup for long-running bots

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Next Steps

This is the foundation for more advanced features:
- Technical indicators
- Trading strategies
- Risk management
- Portfolio tracking
- Alert systems

## License

MIT License - Feel free to modify and use for your projects.

## Disclaimer

This bot is for educational and research purposes. Always test thoroughly before any real trading activities.