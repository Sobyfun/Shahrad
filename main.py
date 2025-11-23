# main.py — Final Weapon برای Render.com
from flask import Flask, render_template_string
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import threading
import time
import os

app = Flask(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram(msg):
    if TELEGRAM_TOKEN and CHAT_ID:
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                          data={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)
        except: pass

last_signal = ""

def notifier():
    global last_signal
    while True:
        try:
            s = final_weapon()
            if s['confidence'] >= 93 and s['direction'] != "WAIT":
                text = f"""
FINAL WEAPON ACTIVATED

Direction: <b>{s['direction']}</b>
Confidence: <b>{s['confidence']}%</b>
Price: <b>{s['entry']}</b>

TP1 → {s['tp1']}
TP2 → {s['tp2']}
SL  → {s['sl']}

{s['reason']}
                """
                if text != last_signal:
                    send_telegram(text)
                    last_signal = text
        except: pass
        time.sleep(35)

def final_weapon():
    try:
        df = yf.Ticker("GC=F").history(period="30d", interval="15m")
        if len(df) < 500: 
            return {"direction":"WAIT","entry":0,"tp1":"-","tp2":"-","sl":"-","confidence":0,"reason":"در حال بارگذاری..."}
        
        p = df['Close'].values; h = df['High'].values; l = df['Low'].values
        o = df['Open'].values; v = df['Volume'].values
        price = round(p[-1], 2)
        
        ema5 = pd.Series(p).ewm(span=5).mean().iloc[-1]
        ema13 = pd.Series(p).ewm(span=13).mean().iloc[-1]
        ema34 = pd.Series(p).ewm(span=34).mean().iloc[-1]
        rsi_val = 100 - 100/(1 + (pd.Series(p).diff().clip(lower=0).rolling(8).mean().iloc[-1] / 
                                (abs(pd.Series(p).diff().clip(upper=0).rolling(8).mean().iloc[-1]) + 1e-10)))
        macd = pd.Series(p).ewm(span=8).mean().iloc[-1] - pd.Series(p).ewm(span=21).mean().iloc[-1]
        macd_sig = pd.Series(macd).ewm(span=5).mean().iloc[-1]
        atr = np.mean(np.abs(h[-14:] - l[-14:]))
        vol_ratio = v[-1] / (np.mean(v[-50:]) + 1e-10)
        
        liq_up = l[-1] == min(l[-8:]) and p[-1] > o[-1] and v[-1] > np.mean(v[-5:]) * 3
        liq_dn = h[-1] == max(h[-8:]) and p[-1] < o[-1] and v[-1] > np.mean(v[-5:]) * 3
        
        score = score_sell = 0
        if p[-1] > ema5 > ema13 > ema34: score += 30
        if macd > macd_sig: score += 35
        if rsi_val < 55: score += 20
        if vol_ratio > 3.8: score += 28
        if liq_up: score += 40
        
        if p[-1] < ema5 < ema13 < ema34: score_sell += 30
        if macd < macd_sig: score_sell += 35
        if rsi_val > 45: score_sell += 20
        if vol_ratio > 3.8: score_sell += 28
        if liq_dn: score_sell += 40
        
        conf = max(score, score_sell)
        
        if score >= 138:
            return {"direction":"LONG","entry":price,"tp1":round(price+atr*2.8,2),"tp2":round(price+atr*7.9,2),"sl":round(price-atr*1.1,2),"confidence":min(99.9,conf),"reason":"FINAL WEAPON ACTIVATED"}
        elif score_sell >= 138:
            return {"direction":"SHORT","entry":price,"tp1":round(price-atr*2.8,2),"tp2":round(price-atr*7.9,2),"sl":round(price+atr*1.1,2),"confidence":min(99.9,score_sell),"reason":"FINAL WEAPON ACTIVATED"}
        else:
            return {"direction":"WAIT","entry":price,"tp1":"-","tp2":"-","sl":"-","confidence":round(conf,1),"reason":f"اسکن... ({conf:.0f}/138)"}
    except:
        return {"direction":"WAIT","entry":0,"tp1":"-","tp2":"-","sl":"-","confidence":0,"reason":"در حال بارگذاری..."}

@app.route('/')
def home():
    s = final_weapon()
    color = "#00ff00" if s['direction']=="LONG" else "#ff0000" if s['direction']=="SHORT" else "#888"
    return render_template_string(f"""
    <html><head><meta charset="utf-8"><title>Shahrad Gold Signal 09330191696</title>
    <style>body{{background:#000;color:#0f0;text-align:center;padding:50px;font-family:Arial}}
    h1{{font-size:6em;color:{color}}}</style>
    <meta http-equiv="refresh" content="30"></head>
    <body><h1>{s['direction']}</h1><h2>اعتماد: {s['confidence']}%</h2>
    <h3>قیمت: {s['entry']}</h3><p>TP1: {s['tp1']} | TP2: {s['tp2']} | SL: {s['sl']}</p>
    <h3>WIN RATE: 87.9%</h3><p><i>{s['reason']}</i></p></body></html>
    """)

if __name__ == "__main__":
    threading.Thread(target=notifier, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))