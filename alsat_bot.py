import os
import asyncio
import alpaca_trade_api as tradeapi
from telegram import Bot
from tradingview_ta import TA_Handler, Interval

# --- AYARLAR ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
ALPACA_KEY = os.getenv("ALPACA_API_KEY")
ALPACA_SECRET = os.getenv("ALPACA_SECRET_KEY")
BASE_URL = 'https://paper-api.alpaca.markets'

# Alpaca Bağlantısı
alpaca = tradeapi.REST(ALPACA_KEY, ALPACA_SECRET, BASE_URL, api_version='v2')

def piyasa_taramasi():
    hisseler = ["NVDA", "TSLA", "AAPL", "PLTR", "AMD"]
    firsatlar = []
    for sembol in hisseler:
        try:
            h = TA_Handler(symbol=sembol, screener="america", exchange="NASDAQ", interval=Interval.INTERVAL_1_DAY)
            analiz = h.get_analysis()
            fiyat = analiz.indicators['close']
            atr = analiz.indicators['ATR']
            
            if "STRONG_BUY" in analiz.summary['RECOMMENDATION']:
                sl = fiyat - (atr * 1.5)
                tp = fiyat + (atr * 3.0)
                firsatlar.append({"sembol": sembol, "fiyat": fiyat, "sl": sl, "tp": tp})
        except: continue
    return firsatlar

async def emir_ve_bildirim():
    firsatlar = piyasa_taramasi()
    if not firsatlar:
        return # Fırsat yoksa mesaj atıp rahatsız etmesin

    bot = Bot(token=TELEGRAM_TOKEN)
    islem_ozeti = "💰 *OTOMATİK ALIM-SATIM GERÇEKLEŞTİ* 💰\n\n"

    for f in firsatlar:
        try:
            alpaca.submit_order(
                symbol=f['sembol'],
                qty=1, 
                side='buy',
                type='market',
                time_in_force='gtc',
                order_class='bracket',
                take_profit={'limit_price': round(f['tp'], 2)},
                stop_loss={'stop_price': round(f['sl'], 2)}
            )
            islem_ozeti += f"✅ *{f['sembol']}* alındı.\n   🎯 Hedef: `${f['tp']:.2f}`\n   🛑 Stop: `${f['sl']:.2f}`\n\n"
        except Exception as e:
            islem_ozeti += f"❌ *{f['sembol']}* hatası: `{str(e)}` \n\n"

    await bot.send_message(chat_id=CHAT_ID, text=islem_ozeti, parse_mode='Markdown')

if __name__ == "__main__":
    asyncio.run(emir_ve_bildirim())
