import requests
import json
import os
from datetime import datetime, timedelta

INDODAX_SUMMARIES_URL = "https://indodax.com/api/summaries"
INDODAX_TRADES_URL = "https://indodax.com/api/trades/"
INDODAX_DEPTH_URL = "https://indodax.com/api/depth/"

HEAVY_COINS = ['BTC', 'ETH', 'USDT', 'USDC', 'BNB', 'SOL', 'XRP', 'TRX', 'DOGE', 'ADA', 'MATIC']

NARRATIVE_MAP = {
    'MEME_AI': ['GOAT', 'GRIFFAIN', 'ACT', 'AVA', 'FARTCOIN', 'PEPE', 'SHIB', 'BONK', 'FLOKI', 'MEME', 'WIF', 'POPCAT'],
    'LAYER1_DEFI': ['SUI', 'APT', 'AVAX', 'NEAR', 'FTM', 'INJ', 'SEI', 'TIA', 'RENDER', 'FET'],
    'GAMING_NFT': ['GALA', 'ILV', 'SAND', 'MANA', 'AXS', 'ALICE', 'PIEVERSE']
}

HISTORY_FILE = 'signal_history.json'

def get_narrative(symbol):
    for category, symbols in NARRATIVE_MAP.items():
        if symbol in symbols:
            return category
    return 'ALTCOIN_MICRO'

def get_wib_time():
    wib_now = datetime.utcnow() + timedelta(hours=7)
    return wib_now.strftime("%d %b %Y - %H:%M:%S WIB")

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history[:30], f, indent=4)

def update_signal_history(current_tickers, active_signals):
    history = load_history()
    for item in history:
        pair_id = f"{item['symbol'].lower()}_idr"
        if pair_id in current_tickers:
            try:
                current_price = float(current_tickers[pair_id].get('last', 0))
                if current_price > 0:
                    item['current_price'] = current_price
                    if current_price > item.get('max_price_seen', current_price):
                        item['max_price_seen'] = current_price
                    
                    peak_gain = round(((item['max_price_seen'] - item['entry_price']) / item['entry_price']) * 100, 1)
                    current_gain = round(((current_price - item['entry_price']) / item['entry_price']) * 100, 1)
                    
                    item['peak_gain_pct'] = peak_gain
                    item['current_gain_pct'] = current_gain

                    if peak_gain >= 15.0:
                        item['status'] = '🔥 PUMP SUCCESS'
                    elif current_gain <= -5.0:
                        item['status'] = '🛑 CUT LOSS'
            except Exception:
                continue

    existing_symbols = [h['symbol'] for h in history]
    for sig in active_signals:
        if sig['symbol'] not in existing_symbols:
            history.insert(0, {
                'symbol': sig['symbol'],
                'narrative': sig['narrative'],
                'entry_price': sig['price_idr'],
                'max_price_seen': sig['price_idr'],
                'current_price': sig['price_idr'],
                'peak_gain_pct': 0.0,
                'current_gain_pct': 0.0,
                'status': '⏳ MONITORING',
                'entry_time': get_wib_time()
            })

    save_history(history)
    return history

def run_ultra_early_scanner():
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        res = requests.get(INDODAX_SUMMARIES_URL, headers=headers, timeout=10)
        if res.status_code != 200:
            print("[ERROR] Gagal mengambil data summaries.")
            return
        tickers = res.json().get('tickers', {})
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        return

    early_signals = []

    for pair_id, data in tickers.items():
        if not pair_id.endswith('_idr'):
            continue
        
        symbol = pair_id.replace('_idr', '').upper()
        if symbol in HEAVY_COINS:
            continue

        try:
            last_price = float(data.get('last', 0))
            low_24h = float(data.get('low', 0))
            vol_idr = float(data.get('vol_idr', 0))

            # Filter volume minimal Rp 10 Juta (agar lebih banyak koin potensial terjangkau)
            if last_price <= 0 or low_24h <= 0 or vol_idr < 10_000_000:
                continue

            # SYARAT 1: MASIH DI BOTTOM (+0% s/d +10% dari Low 24h)
            gain_from_bottom = round(((last_price - low_24h) / low_24h) * 100, 1)
            if gain_from_bottom > 10.0:
                continue

            # SYARAT 2: TRANSAKSI TERKINI (Haka Dini)
            t_res = requests.get(f"{INDODAX_TRADES_URL}{pair_id}", headers=headers, timeout=4)
            if t_res.status_code != 200:
                continue
            
            trades = t_res.json()
            if not isinstance(trades, list) or len(trades) < 5:
                continue

            buy_count = 0
            recent_buy_idr = 0
            
            for t in trades[:15]:
                if t.get('type') == 'buy':
                    p = float(t.get('price', 0))
                    a = float(t.get('amount', 0))
                    val = p * a
                    recent_buy_idr += val
                    if val >= 300_000:  # Minimal 1x transaksi Haka Rp300rb
                        buy_count += 1

            # SYARAT 3: TEMBOK JUAL (Top 5 Ask <= 30 Juta)
            d_res = requests.get(f"{INDODAX_DEPTH_URL}{pair_id}", headers=headers, timeout=4)
            thin_wall = False
            top_5_sell_idr = 0
            
            if d_res.status_code == 200:
                depth = d_res.json()
                sell_orders = depth.get('sell', [])
                if isinstance(sell_orders, list):
                    top_5_sell_idr = sum(float(i[0]) * float(i[1]) for i in sell_orders[:5])
                    if top_5_sell_idr <= 30_000_000:  # Batas tembok jual hingga Rp30 Juta
                        thin_wall = True

            # Lolos jika total Haka terkini >= Rp 1 Juta dan tembok relatif tipis
            if (buy_count >= 1 and recent_buy_idr >= 1_000_000 and thin_wall) or gain_from_bottom <= 3.0:
                status_tag = "⚡ READY TO EXPLODE"
                if top_5_sell_idr <= 10_000_000:
                    status_tag = "🔥 ULTRA THIN WALL"

                early_signals.append({
                    'symbol': symbol,
                    'narrative': get_narrative(symbol),
                    'price_idr': last_price,
                    'gain_from_bottom': gain_from_bottom,
                    'recent_buy_idr': round(recent_buy_idr),
                    'top_5_sell_idr': round(top_5_sell_idr),
                    'vol_24h_idr': round(vol_idr),
                    'status_tag': status_tag,
                    'trade_url': f"https://indodax.com/market/{pair_id}",
                    'timestamp': get_wib_time()
                })

        except Exception:
            continue

    # Urutkan koin berdasarkan tembok terdeteksi paling tipis
    early_signals.sort(key=lambda x: x['top_5_sell_idr'])

    history_data = update_signal_history(tickers, early_signals[:15])

    output_data = {
        'updated_at': get_wib_time(),
        'total_signals': len(early_signals),
        'signals': early_signals[:15],
        'history': history_data[:10]
    }

    with open('signals.json', 'w') as f:
        json.dump(output_data, f, indent=4)

    with open('decoupling_signals.json', 'w') as f:
        json.dump(output_data, f, indent=4)

    print(f"[SUCCESS] Selesai pada {get_wib_time()}. Ditemukan {len(early_signals)} koin.")

if __name__ == "__main__":
    run_ultra_early_scanner()
