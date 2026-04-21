import pandas as pd
import pandas_ta as ta

def load_and_prepare_data_for_grid(filepath):
    df = pd.read_csv(filepath, index_col='Open time', parse_dates=True)
    df['EMA_20'] = ta.ema(df['Close'], length=20)
    df['EMA_100'] = ta.ema(df['Close'], length=100)
    df['ATR_14'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
    df.dropna(inplace=True)
    return df

def run_and_get_trades(df, fast_ema_col, slow_ema_col, discount_mult, sl_mult, trail_trigger, trail_drop):
    capital = 1000.0
    position = 0.0
    entry_price = 0.0
    stop_loss = 0.0
    trailing_activation_price = 0.0
    
    trades = []
    
    for i in range(1, len(df)):
        yesterday = df.iloc[i-1]
        today = df.iloc[i]
        
        if position == 0:
            if yesterday[fast_ema_col] > yesterday[slow_ema_col]:
                limit_price = yesterday[fast_ema_col] - (yesterday['ATR_14'] * discount_mult)
                
                if yesterday['Close'] > limit_price and today['Low'] <= limit_price:
                    potential_stop_loss = limit_price - (yesterday['ATR_14'] * sl_mult)
                    trailing_activation_price = limit_price * trail_trigger
                    
                    if today['Low'] <= potential_stop_loss:
                        trades.append({
                            'Date': today.name.strftime('%Y-%m-%d'),
                            'Type': 'LOSS_INTRA',
                            'Entry': round(limit_price, 2),
                            'Exit': round(potential_stop_loss, 2),
                            'Exit_Date': today.name.strftime('%Y-%m-%d'),
                            'Profit_%': round(((potential_stop_loss/limit_price)-1)*100, 2)
                        })
                    else:
                        entry_price = limit_price
                        stop_loss = potential_stop_loss
                        position = capital / entry_price
                        capital = 0.0
                        
                        trades.append({
                            'Date': today.name.strftime('%Y-%m-%d'),
                            'Type': 'ENTRY',
                            'Entry': round(entry_price, 2)
                        })
                        
        elif position > 0:
            if today['Low'] <= stop_loss:
                exit_price = stop_loss
                capital = position * exit_price
                for t in reversed(trades):
                    if t['Type'] == 'ENTRY' and 'Exit' not in t:
                        t['Exit'] = round(exit_price, 2)
                        t['Exit_Type'] = 'EXIT_STOP_OR_TRAIL'
                        t['Profit_%'] = round(((exit_price / t['Entry']) - 1) * 100, 2)
                        t['Exit_Date'] = today.name.strftime('%Y-%m-%d')
                        break
                position = 0.0
            else:
                if yesterday['High'] >= trailing_activation_price:
                    new_stop = yesterday['High'] * trail_drop
                    if new_stop > stop_loss:
                        stop_loss = new_stop

    if position > 0:
        exit_price = df.iloc[-1]['Close']
        capital = position * exit_price
        for t in reversed(trades):
            if t['Type'] == 'ENTRY' and 'Exit' not in t:
                t['Exit'] = round(exit_price, 2)
                t['Exit_Type'] = 'EXIT_END'
                t['Profit_%'] = round(((exit_price / t['Entry']) - 1) * 100, 2)
                t['Exit_Date'] = df.iloc[-1].name.strftime('%Y-%m-%d')
                break

    return [t for t in trades if 'Profit_%' in t]

def main():
    print("Caricamento dati USDC...")
    df_usdc = load_and_prepare_data_for_grid('data/SOLUSDC_1d.csv')
    
    # Config Rank 1 (Drop 3%)
    trades_rank1 = run_and_get_trades(df_usdc, 'EMA_20', 'EMA_100', 1.0, 4.5, 1.05, 0.97)
    df1 = pd.DataFrame(trades_rank1)
    df1.to_csv('risultati/trades_usdc_rank1_drop3.csv', index=False)
    
    # Config Rank 4 (Drop 5%)
    trades_rank4 = run_and_get_trades(df_usdc, 'EMA_20', 'EMA_100', 1.0, 4.5, 1.05, 0.95)
    df4 = pd.DataFrame(trades_rank4)
    df4.to_csv('risultati/trades_usdc_rank4_drop5.csv', index=False)
    
    with open('risultati/confronto_trades_top.md', 'w') as f:
        f.write("# Confronto Trade: Rank 1 (Drop 3%) vs Rank 4 (Drop 5%)\\n\\n")
        f.write("## Rank 1 (EMA 20, Drop 3%)\\n")
        f.write(df1.to_markdown(index=False) + "\\n\\n")
        f.write("## Rank 4 (EMA 20, Drop 5%)\\n")
        f.write(df4.to_markdown(index=False) + "\\n")

    print("File generati in risultati/confronto_trades_top.md")

if __name__ == "__main__":
    main()
