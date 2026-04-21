import os
import pandas as pd
from binance.client import Client
from datetime import datetime

def download_historical_data(symbol, interval, start_str, end_str=None):
    """
    Scarica i dati storici da Binance e li salva in un file CSV.
    """
    print(f"Scaricamento dati per {symbol} ({interval}) dal {start_str}...")
    
    # Inizializza il client Binance (senza chiavi per i dati pubblici)
    client = Client()
    
    # Recupera i klines
    klines = client.get_historical_klines(symbol, interval, start_str, end_str)
    
    # Crea il DataFrame
    columns = [
        'Open time', 'Open', 'High', 'Low', 'Close', 'Volume', 
        'Close time', 'Quote asset volume', 'Number of trades',
        'Taker buy base asset volume', 'Taker buy quote asset volume', 'Ignore'
    ]
    df = pd.DataFrame(klines, columns=columns)
    
    # Pulisci e formatta il DataFrame
    df['Open time'] = pd.to_datetime(df['Open time'], unit='ms')
    df.set_index('Open time', inplace=True)
    
    # Mantieni solo le colonne necessarie e converti in float
    columns_to_keep = ['Open', 'High', 'Low', 'Close', 'Volume']
    df = df[columns_to_keep].astype(float)
    
    # Salva in CSV
    os.makedirs('data', exist_ok=True)
    filename = f"data/{symbol}_{interval}.csv"
    df.to_csv(filename)
    print(f"Dati salvati in {filename}. Totale candele: {len(df)}")
    
    return df

if __name__ == "__main__":
    # Scarica dati giornalieri e a 4 ore per Solana contro USDT (Ultimi 4 anni)
    symbol = "SOLUSDT"
    try:
        download_historical_data(symbol, Client.KLINE_INTERVAL_1DAY, "2020-01-01")
        download_historical_data(symbol, Client.KLINE_INTERVAL_4HOUR, "2020-01-01")
    except Exception as e:
        print(f"Errore nello scaricamento di {symbol}: {e}")
