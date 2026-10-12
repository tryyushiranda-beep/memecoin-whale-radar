import requests
import time
import json

# ==========================================
# PARAMETER AMAN: PAUS MENENGAH (ANTI KOIN ABAL-ABAL)
# ==========================================
MIN_BUY_WALL_IDR = 30_000_000        # Minimal Tembok Beli Rp 30 Juta (Bukan Ritel)
MIN_VOL_24H_IDR = 100_000_000        # Minimal Volume 24j Rp 100 Juta (Bukan Koin Mati)
MAX_VOL_24H_IDR = 5_000_000_000      # Maksimal Volume 24j Rp 5 Miliar (Koin Ringan)

INDODAX_SUMMARIES_URL = "https://indodax.com/api/summaries"
INDODAX_DEPTH_URL = "https://indodax.com/api/depth/"

def get_cheap_lowcap_pairs():
    try:
        response = requests.get(INDODAX_SUMMARIES_URL, timeout=10).json()
        tickers = response.get('tickers', {})
        
        valid_pairs = []
        for pair_id, data in tickers.items():
            if pair_id.endswith('_idr'):
                try:
                    last_price = float(data.get('last', 0))
                    vol_idr = float(data.get('vol_idr', 0))
                    high_24h = float(data.get('high', 0))
                    
                    estimated_mcap_idr = vol_idr * 12.5 
                    price_from_high_pct = ((high_24h - last_price) / high_24h) * 100 if high_24h > 0 else 0
                except (ValueError, TypeError):
                    continue
                
                # Hanya pilih koin yang aktif (vol >= 100M) dan tidak di harga puncak
                if MIN_VOL_24H_IDR <= vol_idr <= MAX_VOL_24H_IDR and last_price > 0:
                    valid_pairs.append({
                        'id': pair_id,
                        'symbol': pair_id.replace('_idr', '').upper(),
                        'price': last_price,
                        'vol_24h': vol_idr,
                        'mcap_idr': estimated_mcap_idr,
                        'discount_pct': round(price_from_high_pct, 1)
                    })
        return valid_pairs
    except Exception as e:
        print(f"[ERROR] Gagal mengambil data bursa: {e}")
        return []

def analyze_whale_buy_wall(pair_id):
    url = f"{INDODAX_DEPTH_URL}{pair_id}"
    try:
        data = requests.get(url, timeout=5).json()
        bids = data.get('buy', [])
        
        if not bids:
            return 0

        # Hitung murni total modal Tembok Beli di 5 antrean Beli (Bids) teratas
        buy_wall_total = 0
        for bid in bids[:5]:
            try:
                price = float(bid[0])
                vol = float(bid[1])
                buy_wall_total += price * vol
            except (IndexError, ValueError, TypeError):
                continue

        return buy_wall_total
    except Exception:
        return 0

def run_scanner():
    print("\n==================================================")
    print("  INDODAX WHALE RADAR: SAFE PAUS SCANNER          ")
    print("==================================================")
    
    pairs = get_cheap_lowcap_pairs()
    valid_signals = []

    for pair in pairs:
        pair_id = pair['id']
        symbol = pair['symbol']
        price = pair['price']
        
        time.sleep(0.1)

        buy_wall_idr = analyze_whale_buy_wall(pair_id)
        if buy_wall_idr < MIN_BUY_WALL_IDR:
            continue

        signal_data = {
            'symbol': symbol,
            'price_idr': price,
            'mcap_idr': pair['mcap_idr'],
            'buy_wall_idr': round(buy_wall_idr),
            'vol_24h_idr': round(pair['vol_24h']),
            'discount_pct': pair['discount_pct'],
            'potential': 'Target Pump Besok',
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        }
        valid_signals.append(signal_data)
        print(f"🔥 [WHALE FOUND] {symbol} | Price: Rp {price:,.0f} | Wall: Rp {buy_wall_idr:,.0f}")

    with open('signals.json', 'w') as f:
        json.dump(valid_signals, f, indent=4)
        
    print(f"[{time.strftime('%H:%M:%S')}] Pemindaian selesai. {len(valid_signals)} koin berkualitas tersimpan.")

if __name__ == "__main__":
    run_scanner()
