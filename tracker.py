import requests
import time
import json

INDODAX_SUMMARIES_URL = "https://indodax.com/api/summaries"
INDODAX_DEPTH_URL = "https://indodax.com/api/depth/"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_active_indodax_pairs():
    try:
        response = requests.get(INDODAX_SUMMARIES_URL, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return []
            
        tickers = response.json().get('tickers', {})
        pairs = []
        
        for pair_id, data in tickers.items():
            if pair_id.endswith('_idr'):
                try:
                    last_price = float(data.get('last', 0))
                    vol_idr = float(data.get('vol_idr', 0))
                    high_24h = float(data.get('high', 0))
                    
                    price_from_high_pct = ((high_24h - last_price) / high_24h) * 100 if high_24h > 0 else 0
                except (ValueError, TypeError):
                    continue
                
                # Cukup pastikan ada transaksi 24 jam (volume > Rp 1 Juta)
                if vol_idr >= 1_000_000 and last_price > 0:
                    pairs.append({
                        'id': pair_id,
                        'symbol': pair_id.replace('_idr', '').upper(),
                        'price': last_price,
                        'vol_24h': vol_idr,
                        'discount_pct': round(price_from_high_pct, 1)
                    })
        
        # Urutkan koin berdasarkan volume harian tertinggi
        pairs.sort(key=lambda x: x['vol_24h'], reverse=True)
        return pairs[:30]  # Ambil 30 koin teraktif agar scanning kilat
    except Exception as e:
        print(f"[ERROR] Summaries: {e}")
        return []

def analyze_whale_buy_wall(pair_id):
    url = f"{INDODAX_DEPTH_URL}{pair_id}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=4)
        if response.status_code != 200:
            return 0

        data = response.json()
        bids = data.get('buy', [])
        if not bids:
            return 0

        buy_wall_total = 0
        for bid in bids[:10]:
            try:
                price = float(bid[0])
                vol = float(bid[1])
                buy_wall_total += (price * vol)
            except (IndexError, ValueError, TypeError):
                continue

        return buy_wall_total
    except Exception:
        return 0

def run_scanner():
    print("\n==================================================")
    print("  INDODAX SPOT RADAR: GUARANTEED SIGNAL SCANNER   ")
    print("==================================================")
    
    start_time = time.time()
    pairs = get_active_indodax_pairs()
    valid_signals = []

    for pair in pairs:
        pair_id = pair['id']
        symbol = pair['symbol']
        price = pair['price']
        vol_24h = pair['vol_24h']
        
        buy_wall_idr = analyze_whale_buy_wall(pair_id)
        
        # Hanya saring jika ada antrean beli murni (> Rp 1 Juta)
        if buy_wall_idr < 1_000_000:
            continue

        signal_data = {
            'symbol': symbol,
            'price_idr': price,
            'mcap_idr': vol_24h * 10,
            'buy_wall_idr': round(buy_wall_idr),
            'vol_24h_idr': round(vol_24h),
            'discount_pct': pair['discount_pct'],
            'potential': 'Target Pump',
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        valid_signals.append(signal_data)
        print(f"🔥 [SUCCESS] {symbol} | Price: Rp {price:,.0f} | Buy Wall: Rp {buy_wall_idr:,.0f}")

    # Simpan hasil pemindaian
    with open('signals.json', 'w') as f:
        json.dump(valid_signals, f, indent=4)
        
    elapsed = round(time.time() - start_time, 2)
    print(f"\n[{time.strftime('%H:%M:%S')}] Selesai dalam {elapsed} detik. {len(valid_signals)} koin tersimpan.")

if __name__ == "__main__":
    run_scanner()
