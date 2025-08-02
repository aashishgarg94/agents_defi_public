import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import desc
from src.aizen.database import SessionLocal
from src.aizen.models.crypto_price import CryptoPrice
from src.aizen.signals.technical_indicators import TechnicalIndicators

TICKER = ['BTC-USD', 'ETH-USD']
db: Session = SessionLocal()

def fetch_and_store_crypto_data():
    """Fetch latest crypto data from the last 5 minutes and store only the most recent entry in the database."""

    try:
        for ticker in TICKER:
            # Fetch only the last 5 minutes of data
            start_time = datetime.utcnow() - timedelta(minutes=5)

            data = yf.download(ticker, start=start_time, interval="1m")

            if data.empty:
                print(f"No data available for {ticker}")
                continue

            latest_row = data.iloc[-1]
            latest_timestamp = data.index[-1].to_pydatetime() 

            df = fetch_prices(ticker, 26)

            technical_indicators = TechnicalIndicators(df)
            
            df = technical_indicators.calculate_technical_indicators()

            rsi = float(df['RSI'].iloc[-1])
            bb_upper = float(df['BB_upper'].iloc[-1])
            bb_middle = float(df['BB_middle'].iloc[-1])
            bb_lower = float(df['BB_lower'].iloc[-1])
            volatility = float(df["Volatility"].iloc[-1])
            macd = float(df['MACD'].iloc[-1])
            macd_signal = float(df['MACD_signal'].iloc[-1])
            macd_histogram = float(df['MACD_histogram'].iloc[-1])
            atr = float(df["ATR"].iloc[-1])
            price_range = float(df['Price_Range'].iloc[-1])
            vwap = float(df['VWAP'].iloc[-1])

            new_entry = CryptoPrice(
                ticker=ticker,
                date=latest_timestamp,  
                open_price = float(latest_row['Open'].iloc[0]),
                high_price = float(latest_row['High'].iloc[0]),
                low_price = float(latest_row['Low'].iloc[0]),
                close_price = float(latest_row['Close'].iloc[0]),
                volume = int(latest_row['Volume'].iloc[0]) if not pd.isna(latest_row['Volume'].iloc[0]) else 0,
                rsi = rsi,
                bb_upper = bb_upper,
                bb_middle = bb_middle,
                bb_lower = bb_lower,
                volatility = volatility,
                macd = macd,
                macd_signal = macd_signal,
                macd_histogram = macd_histogram,
                atr = atr,
                price_range = price_range,
                vwap = vwap
            )

            db.add(new_entry)

        db.commit()
    except Exception as e:
        print(f"Unexpected error: {e}")
    
    finally:
        db.close()

def fetch_prices(ticker, period):
    """Fetch the latest 'period' rows from CryptoPrice for calculations."""
    prices = db.query(
        CryptoPrice.close_price,
        CryptoPrice.high_price,
        CryptoPrice.low_price,
        CryptoPrice.volume
        ).filter(CryptoPrice.ticker == ticker).order_by(desc(CryptoPrice.date)).limit(period).all()
    
    if not prices or len(prices) < period:
        return None

    df = pd.DataFrame(prices, columns=['price', 'High', 'Low', 'Volume'])
    return df.iloc[::-1]  # Reverse to maintain chronological order

if __name__ == "__main__":
    fetch_and_store_crypto_data()
