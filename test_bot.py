from binance.client import Client
import time, requests

API_KEY = "SIk7PEAT6xofb4tPesXsMzwTkmr0CoF0euJMGw8yLSNjhoOzYYJMTQtkufmQVrr7"
API_SECRET = "kQG9peohGbZ70dKBGbMbTolBpRNSq57UQHwThrsZBxcnONVpxM6DtiXQkUPizBwO"

client = Client(API_KEY, API_SECRET, testnet=True)
client.FUTURES_URL = 'https://testnet.binancefuture.com'

try:
    srv = requests.get('https://testnet.binancefuture.com/fapi/v1/time', timeout=10).json()
    offset = srv['serverTime'] - int(time.time()*1000)
    client._get_current_timestamp = lambda: int(time.time()*1000) + offset
except: pass

SYMBOL = "BTCUSDT"
QTY = 0.001
STOP_LOSS_PCT = 1.0
TAKE_PROFIT_PCT = 2.0
COOLDOWN = 900 # 15 minute baad hi naya trade

print("=== SAFE BOT WITH COOLDOWN START ===")
last_trade_time = 0

def get_pos():
    try:
        poss = client.futures_position_information(symbol=SYMBOL)
        for p in poss:
            amt = float(p['positionAmt'])
            entry = float(p['entryPrice'])
            if p['symbol'] == SYMBOL:
                return amt, entry
        return 0.0, 0.0
    except Exception as e:
        print(f"Pos Error: {e}")
        return 0.0, 0.0

while True:
    try:
        klines = client.futures_klines(symbol=SYMBOL, interval='5m', limit=30)
        closes = [float(k[4]) for k in klines]
        price = closes[-1]
        ma7 = sum(closes[-7:])/7
        ma25 = sum(closes[-25:])/25
        curr_pos, entry_price = get_pos()

        # 1. PnL Check - Hamesha pehle
        if curr_pos!= 0 and entry_price!= 0:
            pnl_pct = ((price - entry_price)/entry_price*100) if curr_pos > 0 else ((entry_price - price)/entry_price*100)
            print(f"Price:{int(price)} Pos:{curr_pos} Entry:{int(entry_price)} PnL:{round(pnl_pct,2)}%")

            if pnl_pct <= -STOP_LOSS_PCT:
                print(f">>> STOP LOSS {round(pnl_pct,2)}% - Closing")
                side = 'SELL' if curr_pos > 0 else 'BUY'
                client.futures_create_order(symbol=SYMBOL, side=side, type='MARKET', quantity=abs(curr_pos))
                last_trade_time = time.time()
                time.sleep(10)
                continue

            if pnl_pct >= TAKE_PROFIT_PCT:
                print(f">>> TAKE PROFIT {round(pnl_pct,2)}% - Closing")
                side = 'SELL' if curr_pos > 0 else 'BUY'
                client.futures_create_order(symbol=SYMBOL, side=side, type='MARKET', quantity=abs(curr_pos))
                last_trade_time = time.time()
                time.sleep(10)
                continue
        else:
            print(f"Price:{int(price)} | No Position | MA7:{int(ma7)} MA25:{int(ma25)}")

        # 2. Cooldown - Taake bar bar trade na khule (Aapki confusion ki wajah)
        if time.time() - last_trade_time < COOLDOWN:
            print(f"Cooldown... {int(COOLDOWN - (time.time()-last_trade_time))} sec left")
            time.sleep(30)
            continue

        # 3. Signal - Sirf QTY se trade, double nahi
        if ma7 > ma25 and curr_pos <= 0:
            print(">>> BUY SIGNAL")
            # Agar short me ho to pehle close karo
            if curr_pos < 0:
                client.futures_create_order(symbol=SYMBOL, side='BUY', type='MARKET', quantity=abs(curr_pos))
                time.sleep(2)
            client.futures_create_order(symbol=SYMBOL, side='BUY', type='MARKET', quantity=QTY)
            last_trade_time = time.time()

        elif ma7 < ma25 and curr_pos >= 0:
            print(">>> SELL SIGNAL")
            if curr_pos > 0:
                client.futures_create_order(symbol=SYMBOL, side='SELL', type='MARKET', quantity=abs(curr_pos))
                time.sleep(2)
            client.futures_create_order(symbol=SYMBOL, side='SELL', type='MARKET', quantity=QTY)
            last_trade_time = time.time()

        time.sleep(30)
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(10)