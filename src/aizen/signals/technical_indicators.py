import pandas as pd
import numpy as np
from decimal import Decimal

class TechnicalIndicators:
    def __init__(self, df):
        self.df = df

    def calculate_technical_indicators(self):
        self.calculate_rsi()
        self.calculate_bollinger_bands()
        self.calculate_volatility()
        self.calculate_macd()
        self.calculate_atr()
        self.calculate_price_range()
        self.calculate_vwap()

        return self.df

    def calculate_rsi(self, periods=14, price_col='price'):
        """Calculate Relative Strength Index"""
        delta = self.df[price_col].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(window=periods, min_periods=1).mean()
        avg_loss = loss.rolling(window=periods, min_periods=1).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        self.df['RSI'] = rsi
        return self.df

    def calculate_bollinger_bands(self, periods=20, price_col='price'):
        """Calculate Bollinger Bands"""

        sma = self.df[price_col].rolling(window=periods).mean()
        std = self.df[price_col].rolling(window=periods).std()

        self.df['BB_upper'] = sma + (std * 2)
        self.df['BB_middle'] = sma
        self.df['BB_lower'] = sma - (std * 2)

        self.df["BB_upper"] = self.df["BB_upper"].fillna(self.df[price_col].squeeze())
        self.df["BB_middle"] = self.df["BB_middle"].fillna(self.df[price_col].squeeze())
        self.df["BB_lower"] = self.df["BB_lower"].fillna(self.df[price_col].squeeze())

        return self.df

    def calculate_volatility(self, periods=20, price_col='price'):
        """Calculate Volatility"""
        self.df['Volatility'] = self.df[price_col].rolling(window=periods).std()
        self.df["Volatility"] = self.df["Volatility"].fillna(0)
        return self.df

    def calculate_macd(self, fast=12, slow=26, signal=9, price_col='price'):
        """Calculate MACD"""
        ema_fast = self.df[price_col].ewm(span=fast, adjust=False).mean()
        ema_slow = self.df[price_col].ewm(span=slow, adjust=False).mean()

        self.df['MACD'] = ema_fast - ema_slow
        self.df['MACD_signal'] = self.df['MACD'].ewm(span=signal, adjust=False).mean()
        self.df['MACD_histogram'] = self.df['MACD'] - self.df['MACD_signal']
        return self.df

    def calculate_atr(self, periods=14):
        """Calculate Average True Range"""
        high_low = self.df['High'] - self.df['Low']
        high_close = np.abs(self.df['High'] - self.df['price'].shift())
        low_close = np.abs(self.df['Low'] - self.df['price'].shift())

        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        self.df['ATR'] = tr.rolling(window=periods).mean()

        mean_range = (self.df['High'] - self.df['Low']).mean().item()
        self.df["ATR"] = self.df["ATR"].fillna(mean_range)
        return self.df

    def calculate_price_range(self):
        """Calculate Daily Price Range"""
        self.df['Price_Range'] = self.df['High'] - self.df['Low']
        return self.df

    def calculate_vwap(self):
        """Calculate Volume Weighted Average Price (VWAP) using Decimal for precision"""
        
        # Convert all numeric values to Decimal for precision
        self.df['High'] = self.df['High'].apply(Decimal)
        self.df['Low'] = self.df['Low'].apply(Decimal)
        self.df['price'] = self.df['price'].apply(Decimal)
        self.df['Volume'] = self.df['Volume'].apply(Decimal)

        # Calculate Typical Price
        self.df['Typical_Price'] = (self.df['High'] + self.df['Low'] + self.df['price']) / Decimal(3)

        # Compute Cumulative Volume Price and Cumulative Volume
        self.df['Cumulative_VP'] = (self.df['Typical_Price'] * self.df['Volume']).cumsum()
        self.df['Cumulative_Volume'] = self.df['Volume'].cumsum()

        # Compute VWAP safely, avoiding division by zero
        self.df['VWAP'] = self.df.apply(lambda row: row['Cumulative_VP'] / row['Cumulative_Volume'] if row['Cumulative_Volume'] > 0 else Decimal('NaN'), axis=1)

        return self.df[['VWAP']]