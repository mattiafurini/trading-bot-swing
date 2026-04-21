import pandas as pd

df = pd.read_csv('risultati/trades_1m_precision.csv')
df['EntryTime'] = pd.to_datetime(df['EntryTime'])
df['ExitTime'] = pd.to_datetime(df['ExitTime'])
df['Duration'] = df['ExitTime'] - df['EntryTime']

print("Trade Duration (Days):")
print(df['Duration'].dt.days.describe())

df = df.sort_values('EntryTime')
df['TimeSinceLastExit'] = df['EntryTime'] - df['ExitTime'].shift(1)

print("\nTime Since Last Exit (Days):")
print(df['TimeSinceLastExit'].dt.days.describe())
