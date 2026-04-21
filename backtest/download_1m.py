import os
import pandas as pd
from binance.client import Client
from datetime import datetime
from dateutil.relativedelta import relativedelta

def download_1m_data_chunked(symbol, start_date_str):
    client = Client()
    print(f"Inizio scaricamento {symbol} (1m) dal {start_date_str}...")
    
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.now()
    
    current_date = start_date
    os.makedirs('data', exist_ok=True)
    filename = f"data/{symbol}_1m.csv"
    
    # Se il file esiste, lo cancelliamo per riniziare
    if os.path.exists(filename):
        os.remove(filename)
        
    total_candles = 0
    
    while current_date < end_date:
        next_month = current_date + relativedelta(months=1)
        if next_month > end_date:
            next_month = end_date
            
        print(f"Scaricamento mese: {current_date.strftime('%Y-%m')}...", end=" ", flush=True)
        
        start_str = current_date.strftime("%d %b, %Y")
        end_str = next_month.strftime("%d %b, %Y")
        
        klines = client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1MINUTE, start_str, end_str)
        
        if not klines:
            print("Nessun dato.")
            current_date = next_month
            continue
            
        columns = [
            'Open time', 'Open', 'High', 'Low', 'Close', 'Volume', 
            'Close time', 'Quote asset volume', 'Number of trades',
            'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
        ]
        df = pd.DataFrame(klines, columns=columns)
        df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
        df.set_index('Open time', inplace=True)
        columns_to_keep = ['Open', 'High', 'Low', 'Close', 'Volume']
        df = df[columns_to_keep].astype(float)
        
        total_candles += len(df)
        
        # Appendi al CSV
        write_header = not os.path.exists(filename)
        df.to_csv(filename, mode='a', header=write_header)
        
        print(f"Fatto ({len(df)} candele). Totale finora: {total_candles}")
        
        current_date = next_month

    print(f"\nScaricamento completato! Totale candele: {total_candles}")

if __name__ == "__main__":
    download_1m_data_chunked("SOLUSDC", "2024-01-01")
