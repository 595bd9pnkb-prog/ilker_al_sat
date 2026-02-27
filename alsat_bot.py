import os
import asyncio
import json
import alpaca_trade_api as tradeapi
from telegram import Bot
from tradingview_ta import TA_Handler, Interval

# --- AYARLAR ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
ALPACA_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = 'https://paper-api.alpaca.markets' # Sanal hesap URL'si

# Alpaca Bağlantısı
alpaca = tradeapi.REST(ALPACA_KEY, ALPACA_SECRET, BASE_URL, api_version='v2')

def get_vix_status():
    try:
        vix = TA_Handler(symbol="VIX", screener="cfd", exchange="CBOE", interval=Interval.INTERVAL_1_DAY)
        v = vix.get_analysis().indicators['close']
        return v
    except: return 20

def piyasa_avcisi():
    # Odaklanılacak Likit Hisseler
    dev_liste = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "META", "GOOGL", "AMD", "NFLX", "PLTR"]
    firsatlar = []

    for sembol in dev_liste:
        try:
            h = TA_Handler(symbol=sembol, screener="america", exchange="NASDAQ", interval=Interval.INTERVAL_1_DAY)
            analiz = h.get_analysis()
            fiyat = analiz.indicators['close']
            atr = analiz.indicators['ATR']
            
            # Strateji: Strong Buy + RSI 70 altı
            if "STRONG_BUY" in analiz.summary['RECOMMENDATION'] and analiz.indicators['RSI'] < 70:
                sl = fiyat - (atr * 1.5) # Dinamik Stop
                tp = fiyat + (atr * 3.0) # Dinamik Hedef
                firsatlar.append({"sembol": sembol, "fiyat": fiyat, "sl": sl, "tp": tp})
        except: continue
    return firsatlar

async def main():
    vix = get_vix_status()
    if vix > 25:
        msg = "⚠️ VIX yüksek, bugün işlem açılmadı."
        await Bot(TELEGRAM_TOKEN).send_message(CHAT_ID, msg)
        return

    firsatlar = piyasa_avcisi()
    mesaj = "🤖 *OTOMATİK İŞLEM RAPORU* 🤖\n\n"

    for f in firsatlar:
        try:
            # Otomatik Emir Gönderimi (Bracket Order: Alım + Kar Al + Stop Loss)
            alpaca.submit_order(
                symbol=f['sembol'],
                qty=1, # Deneme için her hissesden 1 adet
                side='buy',
                type='market',
                time_in_force='gtc',
                order_class='bracket',
                take_profit={'limit_price': round(f['tp'], 2)},
                stop_loss={'stop_price': round(f['sl'], 2)}
            )
            mesaj += f"✅ *{f['sembol']}* için alım emri verildi.\n🎯 Hedef: ${f['tp']:.2f}\n🛑 Stop: ${f['sl']:.2f}\n\n"
        except Exception as e:
            mesaj += f"❌ *{f['sembol']}* hatası: {str(e)}\n"

    await Bot(TELEGRAM_TOKEN).send_message(CHAT_ID, mesaj, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(main())
