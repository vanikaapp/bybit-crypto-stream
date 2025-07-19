import time
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pybit.unified_trading import HTTP
import websocket
import threading
from collections import deque
import logging
import ssl
import os

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CryptoBot:
    def __init__(self, symbol="BTCUSDT", data_dir="data"):
        """
        Initialize the crypto bot
        
        Args:
            symbol (str): Trading symbol (default: BTCUSDT)
            data_dir (str): Directory to save data files (default: data)
        """
        self.symbol = symbol
        self.data_dir = data_dir
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize Bybit HTTP client for mainnet
        self.session = HTTP(testnet=False)
        
        # Data storage
        self.historical_data = pd.DataFrame()
        self.live_trades = deque(maxlen=10000)  # Store recent trades
        self.current_candle = None
        self.candle_start_time = None
        
        # WebSocket connection
        self.ws = None
        self.ws_thread = None
        self.running = False
        
        # Lock for thread safety
        self.data_lock = threading.Lock()
        
    def get_data_filename(self, suffix="historical"):
        """
        Get the filename for data storage
        
        Args:
            suffix (str): File suffix (default: historical)
        """
        timestamp = datetime.now().strftime("%Y%m%d")
        return os.path.join(self.data_dir, f"{self.symbol}_{suffix}_{timestamp}.csv")
    
    def save_historical_data(self):
        """
        Save historical data to CSV file
        """
        try:
            with self.data_lock:
                if not self.historical_data.empty:
                    filename = self.get_data_filename("historical")
                    self.historical_data.to_csv(filename, index=False)
                    logger.info(f"Historical data saved to {filename} ({len(self.historical_data)} records)")
                    return filename
                else:
                    logger.warning("No historical data to save")
                    return None
        except Exception as e:
            logger.error(f"Error saving historical data: {e}")
            return None
    
    def load_historical_data(self, filename=None):
        """
        Load historical data from CSV file
        
        Args:
            filename (str): Specific filename to load (optional)
        """
        try:
            if filename is None:
                filename = self.get_data_filename("historical")
            
            if os.path.exists(filename):
                df = pd.read_csv(filename)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                
                with self.data_lock:
                    self.historical_data = df
                
                logger.info(f"Historical data loaded from {filename} ({len(df)} records)")
                return df
            else:
                logger.info(f"No existing data file found at {filename}")
                return None
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
            return None
        
    def fetch_historical_data(self, interval="1", hours=48):
        """
        Fetch historical OHLC data from Bybit
        
        Args:
            interval (str): Kline interval (1, 3, 5, 15, 30, 60, 120, 240, 360, 720, D, W, M)
            hours (int): Number of hours to fetch (default: 48)
        """
        try:
            # Calculate start time (48 hours ago)
            end_time = int(time.time() * 1000)
            start_time = end_time - (hours * 60 * 60 * 1000)
            
            logger.info(f"Fetching {hours} hours of {interval}min data for {self.symbol}")
            
            # Fetch kline data
            response = self.session.get_kline(
                category="spot",
                symbol=self.symbol,
                interval=interval,
                start=start_time,
                end=end_time,
                limit=1000
            )
            
            if response['retCode'] == 0:
                klines = response['result']['list']
                
                # Convert to DataFrame
                df = pd.DataFrame(klines, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume', 'turnover'
                ])
                
                # Convert data types
                df['timestamp'] = pd.to_datetime(df['timestamp'].astype(int), unit='ms')
                df['open'] = df['open'].astype(float)
                df['high'] = df['high'].astype(float)
                df['low'] = df['low'].astype(float)
                df['close'] = df['close'].astype(float)
                df['volume'] = df['volume'].astype(float)
                df['turnover'] = df['turnover'].astype(float)
                
                # Sort by timestamp (oldest first)
                df = df.sort_values('timestamp').reset_index(drop=True)
                
                with self.data_lock:
                    self.historical_data = df
                
                logger.info(f"Successfully fetched {len(df)} candles")
                logger.info(f"Data range: {df['timestamp'].iloc[0]} to {df['timestamp'].iloc[-1]}")
                
                # Save historical data to CSV
                self.save_historical_data()
                
                return df
            else:
                logger.error(f"Error fetching data: {response['retMsg']}")
                return None
                
        except Exception as e:
            logger.error(f"Exception while fetching historical data: {e}")
            return None
    
    def initialize_current_candle(self):
        """
        Initialize the current 1-minute candle
        """
        now = datetime.now()
        # Round down to the current minute
        self.candle_start_time = now.replace(second=0, microsecond=0)
        
        self.current_candle = {
            'timestamp': self.candle_start_time,
            'open': None,
            'high': None,
            'low': None,
            'close': None,
            'volume': 0.0,
            'turnover': 0.0,
            'trade_count': 0
        }
        
        logger.info(f"Initialized new candle for {self.candle_start_time}")
    
    def update_current_candle(self, price, volume):
        """
        Update the current candle with new trade data
        
        Args:
            price (float): Trade price
            volume (float): Trade volume
        """
        with self.data_lock:
            if self.current_candle['open'] is None:
                self.current_candle['open'] = price
                self.current_candle['high'] = price
                self.current_candle['low'] = price
            else:
                self.current_candle['high'] = max(self.current_candle['high'], price)
                self.current_candle['low'] = min(self.current_candle['low'], price)
            
            self.current_candle['close'] = price
            self.current_candle['volume'] += volume
            self.current_candle['turnover'] += price * volume
            self.current_candle['trade_count'] += 1
    
    def finalize_candle(self):
        """
        Finalize the current candle and add it to historical data
        """
        with self.data_lock:
            if self.current_candle and self.current_candle['open'] is not None:
                # Create new row for historical data
                new_row = pd.DataFrame([{
                    'timestamp': self.current_candle['timestamp'],
                    'open': self.current_candle['open'],
                    'high': self.current_candle['high'],
                    'low': self.current_candle['low'],
                    'close': self.current_candle['close'],
                    'volume': self.current_candle['volume'],
                    'turnover': self.current_candle['turnover']
                }])
                
                # Add to historical data
                self.historical_data = pd.concat([self.historical_data, new_row], ignore_index=True)
                
                logger.info(f"Finalized candle: O:{self.current_candle['open']:.2f} H:{self.current_candle['high']:.2f} L:{self.current_candle['low']:.2f} C:{self.current_candle['close']:.2f} V:{self.current_candle['volume']:.4f}")
                
                # Save updated data every 10 candles to avoid excessive I/O
                if len(self.historical_data) % 10 == 0:
                    self.save_historical_data()
    
    def on_message(self, ws, message):
        """
        Handle WebSocket messages
        """
        try:
            data = json.loads(message)
            
            # Handle trade data
            if 'topic' in data and 'publicTrade' in data['topic']:
                trades = data.get('data', [])
                
                for trade in trades:
                    price = float(trade['p'])
                    volume = float(trade['v'])
                    timestamp = int(trade['T'])
                    
                    # Store trade
                    self.live_trades.append({
                        'timestamp': timestamp,
                        'price': price,
                        'volume': volume
                    })
                    
                    # Check if we need to start a new candle
                    current_time = datetime.fromtimestamp(timestamp / 1000)
                    current_minute = current_time.replace(second=0, microsecond=0)
                    
                    if self.candle_start_time is None or current_minute > self.candle_start_time:
                        # Finalize previous candle if it exists
                        if self.current_candle is not None:
                            self.finalize_candle()
                        
                        # Start new candle
                        self.candle_start_time = current_minute
                        self.current_candle = {
                            'timestamp': current_minute,
                            'open': price,
                            'high': price,
                            'low': price,
                            'close': price,
                            'volume': volume,
                            'turnover': price * volume,
                            'trade_count': 1
                        }
                    else:
                        # Update current candle
                        self.update_current_candle(price, volume)
                        
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
    
    def on_error(self, ws, error):
        """
        Handle WebSocket errors
        """
        logger.error(f"WebSocket error: {error}")
    
    def on_close(self, ws, close_status_code, close_msg):
        """
        Handle WebSocket close
        """
        logger.info("WebSocket connection closed")
        self.running = False
    
    def on_open(self, ws):
        """
        Handle WebSocket open
        """
        logger.info("WebSocket connection opened")
        
        # Subscribe to public trades
        subscribe_msg = {
            "op": "subscribe",
            "args": [f"publicTrade.{self.symbol}"]
        }
        
        ws.send(json.dumps(subscribe_msg))
        logger.info(f"Subscribed to {self.symbol} trades")
    
    def start_live_stream(self):
        """
        Start the live data stream
        """
        try:
            # Initialize current candle
            self.initialize_current_candle()
            
            # WebSocket URL for Bybit mainnet
            ws_url = "wss://stream.bybit.com/v5/public/spot"
            
            # Create WebSocket connection
            self.ws = websocket.WebSocketApp(
                ws_url,
                on_message=self.on_message,
                on_error=self.on_error,
                on_close=self.on_close,
                on_open=self.on_open
            )
            
            self.running = True
            
            # Start WebSocket in a separate thread with SSL context
            self.ws_thread = threading.Thread(
                target=lambda: self.ws.run_forever(
                    sslopt={"cert_reqs": ssl.CERT_NONE}
                )
            )
            self.ws_thread.daemon = True
            self.ws_thread.start()
            
            logger.info("Live stream started")
            
        except Exception as e:
            logger.error(f"Error starting live stream: {e}")
    
    def stop_live_stream(self):
        """
        Stop the live data stream
        """
        self.running = False
        if self.ws:
            self.ws.close()
        if self.ws_thread:
            self.ws_thread.join(timeout=5)
        
        logger.info("Live stream stopped")
    
    def get_latest_data(self, rows=10):
        """
        Get the latest OHLC data
        
        Args:
            rows (int): Number of latest rows to return
        """
        with self.data_lock:
            if len(self.historical_data) > 0:
                return self.historical_data.tail(rows)
            return pd.DataFrame()
    
    def get_current_candle_info(self):
        """
        Get current candle information
        """
        with self.data_lock:
            if self.current_candle:
                return self.current_candle.copy()
            return None
    
    def run(self):
        """
        Main run method
        """
        try:
            # Step 1: Fetch historical data
            logger.info("Starting crypto bot...")
            historical_data = self.fetch_historical_data()
            
            if historical_data is None:
                logger.error("Failed to fetch historical data")
                return
            
            # Step 2: Start live streaming
            self.start_live_stream()
            
            # Step 3: Keep running and display stats
            while self.running:
                time.sleep(10)  # Update every 10 seconds
                
                # Display current stats
                current_candle = self.get_current_candle_info()
                latest_data = self.get_latest_data(3)
                
                logger.info(f"Historical candles: {len(self.historical_data)}")
                logger.info(f"Live trades received: {len(self.live_trades)}")
                
                if current_candle:
                    logger.info(f"Current candle: {current_candle}")
                
                if not latest_data.empty:
                    logger.info(f"Latest close price: {latest_data['close'].iloc[-1]:.2f}")
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Error in main run loop: {e}")
        finally:
            # Save final data before stopping
            self.save_historical_data()
            self.stop_live_stream()
            logger.info("Bot stopped")

if __name__ == "__main__":
    # Create and run the bot
    bot = CryptoBot(symbol="BTCUSDT")
    bot.run()