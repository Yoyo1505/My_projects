import os
os.makedirs("data", exist_ok=True)
import yfinance as yf
tickers = ["SPY","QQQ","IWM","EFA","EEM","TLT","IEF","GLD","DBC","VNQ","XLE","XLK"]
df = yf.download(tickers, start="2015-01-01", auto_adjust=False, progress=False)["Adj Close"]
df = df[tickers]
df.to_csv("data/adj_close.csv")
print(df.shape, df.index.min(), df.index.max())
print(df.isna().sum().to_dict())
