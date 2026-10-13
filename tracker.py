import requests
import time
import json

# ==========================================
# PARAMETER PURE INDODAX (BYPASS & FAST SCAN)
# ==========================================
MIN_BUY_WALL_IDR = 5_000_000        # Minimal Tembok Beli Bids Rp 5 Juta
MIN_VOL_24H_IDR = 5_000_000         # Minimal Volume Transaksi 24 Jam Rp 5 Juta

INDODAX_SUMMARIES_URL = "https://indodax.com/api/summaries"
INDODAX_DEPTH_URL = "https://indodax.com/api/depth/"

# Header resmi browser agar tidak diblokir Cloudflare/Indodax di GitHub Actions
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_indodax_tickers():
    """Mengambil seluruh data ticker aktif dari pasar Indodax."""
    try:
        response = requests.get(INDODAX_SUMMARIES_URL, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            print(f"[ERROR] API Summaries HTTP Status: {response.status_code}")
            return []
            
        tickers = response.json().get('tickers', {})
        valid_pairs = []
        
        for pair_id, data in tickers.items():
            if pair_id.endswith('_idr'):
                try:
                    last_price = float(data.get('last', 0))
                    vol_idr = float(data.get('vol_idr', 0))
                    high_24h = float(data.get('high', 0))
                    
                    price_from_high_pct = ((high_24h - last_price) / high_24h) * 100 if high_24h > 0 else 0
                except (ValueError, TypeError):
                    continue
                
                if vol_idr >= MIN_VOL_24H_IDR and last_price > 0:
                    valid_pairs.append({
                        'id': pair_id,
                        'symbol': pair_id.replace('_idr', '').upper(),
                        'price': last_price,
                        'vol_24h': vol_idr,
                        'discount_pct': round(price_from_high_pct, 1)
                    })
        return valid_pairs
    except Exception as e:
        print(f"[ERROR] Gagal mengambil data summaries: {e}")
        return []

def analyze_whale_buy_wall(pair_id):
    """Membaca Order Book Bids Indodax langsung."""
    url = f"{INDODAX_DEPTH_URL}{pair_id}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        if response.status_code != 200:
            return 0

        data = response.json()
        bids = data.get('buy', [])
        if not bids:
            return 0

        buy_wall_total = 0
        # Menghitung 10 tingkat antrean beli teratas
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
    print("  INDODAX SPOT RADAR: BYPASS & REALTIME SCANNER   ")
    print("==================================================")
    
    pairs = get_indodax_tickers()
    print(f"[INFO] Ditemukan {len(pairs)} pasangan koin IDR aktif untuk dipindai.")
    
    valid_signals = []

    for pair in pairs:
        pair_id = pair['id']
        symbol = pair['symbol']
        price = pair['price']
        vol_24h = pair['vol_24h']
        
        time.sleep(0.12)  # Delay aman dari pembatasan API

        buy_wall_idr = analyze_whale_buy_wall(pair_id)
        if buy_wall_idr < MIN_BUY_WALL_IDR:
            continue

        signal_data = {
            'symbol': symbol,
            'price_idr': price,
            'mcap_idr': vol_24h * 10,  # Estimasi bobot perputaran
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
        
    print(f"\n[{time.strftime('%H:%M:%S')}] Pemindaian selesai. Total {len(valid_signals)} koin berhasil ditangkap!")

if __name__ == "__main__":
    run_scanner()
