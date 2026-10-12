import requests
import time
import json

# ==========================================
# PARAMETER STRATEGI: WHALE & MARKET CAP (INDODAX)
# ==========================================
MIN_BUY_WALL_IDR = 30_000_000        # Minimal Tembok Penahan Beli Paus Rp 30 Juta
MIN_VOL_24H_IDR = 100_000_000        # Minimal Volume Transaksi 24 Jam Rp 100 Juta
MAX_VOL_24H_IDR = 10_000_000_000     # Maksimal Volume 24 Jam Rp 10 Miliar (Koin Ringan)

INDODAX_SUMMARIES_URL = "https://indodax.com/api/summaries"
INDODAX_DEPTH_URL = "https://indodax.com/api/depth/"

def get_cheap_lowcap_pairs():
    """Mengambil koin IDR ber-Market Cap/Volume ringan di Indodax yang harganya masih diskon."""
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
                    low_24h = float(data.get('low', 0))
                    
                    # Hitung estimasi Market Cap lokal berbasis likuiditas perputaran pasar
                    # Mengukur koin berbobot ringan sampai menengah
                    estimated_mcap_idr = vol_idr * 12.5 
                    
                    # Hitung persentase diskon harga dibanding harga puncak 24 jam terakhir
                    price_from_high_pct = ((high_24h - last_price) / high_24h) * 100 if high_24h > 0 else 0
                except (ValueError, TypeError):
                    continue
                
                # Syarat Koin: Volume aktif, berbobot ringan, dan harga belum terbang (masih di dasar)
                if MIN_VOL_24H_IDR <= vol_idr <= MAX_VOL_24H_IDR and last_price > 0:
                    if price_from_high_pct >= 1.5:  # Minimal 1.5% di bawah harga puncak harian
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
        print(f"[ERROR] Gagal mengambil data bursa Indodax: {e}")
        return []

def analyze_whale_buy_wall(pair_id):
    """Membaca Order Book Indodax untuk mendeteksi Tembok Beli Penahan milik Paus."""
    url = f"{INDODAX_DEPTH_URL}{pair_id}"
    try:
        data = requests.get(url, timeout=5).json()
        bids = data.get('buy', [])
        asks = data.get('sell', [])
        
        if not bids or not asks:
            return 0, False

        # 1. Hitung total modal Tembok Beli Paus di 5 antrean Beli (Bids) teratas
        buy_wall_total = 0
        for bid in bids[:5]:
            try:
                price = float(bid[0])
                vol = float(bid[1])
                buy_wall_total += price * vol
            except (IndexError, ValueError, TypeError):
                continue

        # 2. Hitung total antrean Jual (Asks) di 5 tingkat teratas
        ask_depth_total = 0
        for ask in asks[:5]:
            try:
                price = float(ask[0])
                vol = float(ask[1])
                ask_depth_total += price * vol
            except (IndexError, ValueError, TypeError):
                continue

        # Syarat Jalur Terbang (Thin Ask): Tembok Beli Paus harus lebih kuat dari antrean jual di atasnya
        is_thin_ask = (buy_wall_total > 0) and (buy_wall_total >= ask_depth_total * 0.8)

        return buy_wall_total, is_thin_ask
    except Exception:
        return 0, False

def run_scanner():
    print("\n==================================================")
    print("  INDODAX WHALE RADAR: CHEAP & LOW-CAP SCANNER    ")
    print("==================================================")
    
    pairs = get_cheap_lowcap_pairs()
    valid_signals = []

    for pair in pairs:
        pair_id = pair['id']
        symbol = pair['symbol']
        price = pair['price']
        
        time.sleep(0.12)  # Mencegah Rate Limit API

        # Deteksi keberadaan Tembok Penahan Paus di Order Book Indodax
        buy_wall_idr, is_thin_ask = analyze_whale_buy_wall(pair_id)
        if buy_wall_idr < MIN_BUY_WALL_IDR or not is_thin_ask:
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
        print(f"🔥 [WHALE FOUND] {symbol} | Price: Rp {price:,.0f} | Wall: Rp {buy_wall_idr:,.0f} | Discount: {pair['discount_pct']}%")

    # Ekspor hasil pindaian ke file signals.json
    with open('signals.json', 'w') as f:
        json.dump(valid_signals, f, indent=4)
        
    print(f"[{time.strftime('%H:%M:%S')}] Pemindaian selesai. {len(valid_signals)} koin murah ber-Tembok Paus tersimpan.")

if __name__ == "__main__":
    run_scanner()
