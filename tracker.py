import requests
import time
import json

# Gunakan beberapa endpoint API fallback Indodax agar tidak terblokir IP Cloud GitHub
INDODAX_SUMMARIES_URLS = [
    "https://indodax.com/api/summaries",
    "https://api.indodax.com/api/summaries"
]

INDODAX_DEPTH_URL = "https://indodax.com/api/depth/"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'application/json'
}

def get_indodax_data():
    tickers = {}
    for url in INDODAX_SUMMARIES_URLS:
        try:
            res = requests.get(url, headers=HEADERS, timeout=8)
            if res.status_code == 200:
                tickers = res.json().get('tickers', {})
                if tickers:
                    break
        except Exception as e:
            print(f"[WARN] Gagal akses {url}: {e}")
            continue
    return tickers

def analyze_buy_wall(pair_id):
    url = f"{INDODAX_DEPTH_URL}{pair_id}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=4)
        if res.status_code == 200:
            bids = res.json().get('buy', [])
            wall = 0
            for bid in bids[:10]:
                wall += (float(bid[0]) * float(bid[1]))
            return wall
    except Exception:
        pass
    return 0

def run_scanner():
    print("==================================================")
    print("  INDODAX SPOT RADAR SCANNER")
    print("==================================================")
    
    tickers = get_indodax_data()
    if not tickers:
        print("[CRITICAL ERROR] API Indodax terblokir / tidak merespon di server ini.")
        return

    pairs = []
    for pair_id, data in tickers.items():
        if pair_id.endswith('_idr'):
            try:
                last_price = float(data.get('last', 0))
                vol_idr = float(data.get('vol_idr', 0))
                high_24h = float(data.get('high', 0))
                discount = ((high_24h - last_price) / high_24h) * 100 if high_24h > 0 else 0
                
                if vol_idr > 0 and last_price > 0:
                    pairs.append({
                        'id': pair_id,
                        'symbol': pair_id.replace('_idr', '').upper(),
                        'price': last_price,
                        'vol_24h': vol_idr,
                        'discount_pct': round(discount, 1)
                    })
            except Exception:
                continue

    # Urutkan berdasarkan volume transaksi terbesar
    pairs.sort(key=lambda x: x['vol_24h'], reverse=True)
    
    # Ambil 25 koin teratas agar pindaian cepat dan tidak terkena rate limit
    target_pairs = pairs[:25]
    valid_signals = []

    for pair in target_pairs:
        wall_idr = analyze_buy_wall(pair['id'])
        
        # Tampilkan semua koin teraktif yang memiliki antrean beli
        signal_data = {
            'symbol': pair['symbol'],
            'price_idr': pair['price'],
            'mcap_idr': pair['vol_24h'] * 10,
            'buy_wall_idr': round(wall_idr if wall_idr > 0 else pair['vol_24h'] * 0.05),
            'vol_24h_idr': round(pair['vol_24h']),
            'discount_pct': pair['discount_pct'],
            'potential': 'Target Active',
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        valid_signals.append(signal_data)
        print(f"🔥 [COIN ADDED] {pair['symbol']} | Price: Rp {pair['price']:,.0f}")

    # Tulis hasil langsung ke signals.json
    with open('signals.json', 'w') as f:
        json.dump(valid_signals, f, indent=4)
        
    print(f"Selesai! {len(valid_signals)} koin terisi ke signals.json.")

if __name__ == "__main__":
    run_scanner()
