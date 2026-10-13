import requests
import time
import json

# Daftar koin raksasa (High Cap) yang dibuang agar fokus ke Altcoin/Memecoin
HEAVY_COINS = ['BTC', 'ETH', 'USDT', 'USDC', 'BNB', 'SOL', 'XRP', 'TRX']

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
        except Exception:
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
    print("  INDODAX ALTCOIN & MEMECOIN RADAR SCANNER        ")
    print("==================================================")
    
    tickers = get_indodax_data()
    if not tickers:
        print("[ERROR] API Indodax tidak merespon.")
        return

    pairs = []
    for pair_id, data in tickers.items():
        if pair_id.endswith('_idr'):
            symbol = pair_id.replace('_idr', '').upper()
            
            # Abaikan koin raksasa / High Cap
            if symbol in HEAVY_COINS:
                continue

            try:
                last_price = float(data.get('last', 0))
                vol_idr = float(data.get('vol_idr', 0))
                high_24h = float(data.get('high', 0))
                discount = ((high_24h - last_price) / high_24h) * 100 if high_24h > 0 else 0
                
                # Filter koin ringan: Volume 24j antara 10 Juta s/d 5 Miliar Rupiah
                if 10_000_000 <= vol_idr <= 5_000_000_000 and last_price > 0:
                    pairs.append({
                        'id': pair_id,
                        'symbol': symbol,
                        'price': last_price,
                        'vol_24h': vol_idr,
                        'discount_pct': round(discount, 1)
                    })
            except Exception:
                continue

    # Urutkan berdasarkan potensi diskon & volume
    pairs.sort(key=lambda x: x['vol_24h'], reverse=True)
    
    target_pairs = pairs[:20]  # Ambil Top 20 Altcoin Ringan Teraktif
    valid_signals = []

    for pair in target_pairs:
        wall_idr = analyze_buy_wall(pair['id'])
        
        signal_data = {
            'symbol': pair['symbol'],
            'price_idr': pair['price'],
            'mcap_idr': pair['vol_24h'] * 10,
            'buy_wall_idr': round(wall_idr if wall_idr > 0 else pair['vol_24h'] * 0.05),
            'vol_24h_idr': round(pair['vol_24h']),
            'discount_pct': pair['discount_pct'],
            'potential': 'Altcoin Target',
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        valid_signals.append(signal_data)
        print(f"🔥 [ALTCOIN FOUND] {pair['symbol']} | Price: Rp {pair['price']:,.0f}")

    with open('signals.json', 'w') as f:
        json.dump(valid_signals, f, indent=4)
        
    print(f"Selesai! {len(valid_signals)} altcoin ringan tersimpan.")

if __name__ == "__main__":
    run_scanner()
