import requests
import json
from datetime import datetime, timedelta

INDODAX_SUMMARIES_URL = "https://indodax.com/api/summaries"
INDODAX_TRADES_URL = "https://indodax.com/api/trades/"
INDODAX_DEPTH_URL = "https://indodax.com/api/depth/"

# Koin-koin berkapitalisasi besar yang diabaikan agar fokus ke altcoin/memecoin spekulatif
HEAVY_COINS = ['BTC', 'ETH', 'USDT', 'USDC', 'BNB', 'SOL', 'XRP', 'TRX', 'DOGE', 'ADA', 'MATIC']

def get_wib_time():
    """Mendapatkan jam WIB (UTC+7) murni presisi dari UTC server"""
    wib_now = datetime.utcnow() + timedelta(hours=7)
    return wib_now.strftime("%d %b %Y - %H:%M:%S WIB")

def run_ultra_early_scanner():
    try:
        res = requests.get(INDODAX_SUMMARIES_URL, timeout=10)
        if res.status_code != 200:
            print("[ERROR] Gagal mengambil data summaries Indodax.")
            return
        tickers = res.json().get('tickers', {})
    except Exception as e:
        print(f"[ERROR] Exception: {e}")
        return

    early_signals = []

    print(f"[INFO] Memulai pemindaian Dini Pump pada {get_wib_time()}...")

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

            # Filter koin mati (Volume 24h minimal Rp 15 Juta)
            if last_price <= 0 or low_24h <= 0 or vol_idr < 15_000_000:
                continue

            # SYARAT 1: HARGA MASIH DI BOTTOM (Belum naik lebih dari 8% dari Low 24h)
            gain_from_bottom = round(((last_price - low_24h) / low_24h) * 100, 1)
            if gain_from_bottom > 8.0:
                continue

            # SYARAT 2: CEK TRANSAKSI TERKINI (Mencari Akumulasi Halus)
            t_res = requests.get(f"{INDODAX_TRADES_URL}{pair_id}", timeout=3)
            if t_res.status_code != 200:
                continue
            
            trades = t_res.json()
            if not trades or len(trades) < 10:
                continue

            buy_count = 0
            recent_buy_idr = 0
            
            # Cek 15 transaksi terakhir
            for t in trades[:15]:
                if t.get('type') == 'buy':
                    p = float(t.get('price', 0))
                    a = float(t.get('amount', 0))
                    val = p * a
                    recent_buy_idr += val
                    # Hitung eksekusi beli pecahan sedang (>= Rp 500rb)
                    if val >= 500_000:
                        buy_count += 1

            # SYARAT 3: CEK KEDALAMAN TEMBOK JUAL (Order Book Ask)
            d_res = requests.get(f"{INDODAX_DEPTH_URL}{pair_id}", timeout=3)
            thin_wall = False
            top_5_sell_idr = 0
            
            if d_res.status_code == 200:
                depth = d_res.json()
                sell_orders = depth.get('sell', [])
                
                # Hitung akumulasi nilai Rupiah di 5 antrean jual teratas
                top_5_sell_idr = sum(float(i[0]) * float(i[1]) for i in sell_orders[:5])
                
                # Jika tembok jual 5 tingkat ke atas <= Rp 20 Juta -> SANGAT TIPIS (Mudah Memicu Mega Pump)
                if top_5_sell_idr <= 20_000_000:
                    thin_wall = True

            # DETEKSI PINTU MASUK DINI:
            # - Minimal 2x Haka pecahan sedang
            # - Total Beli terkini >= Rp 2 Juta
            # - Tembok jual tipis
            if buy_count >= 2 and recent_buy_idr >= 2_000_000 and thin_wall:
                status_tag = "⚡ READY TO EXPLODE"
                if top_5_sell_idr <= 8_000_000:
                    status_tag = "🔥 ULTRA THIN WALL"

                early_signals.append({
                    'symbol': symbol,
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

    # Urutkan berdasarkan tembok jual paling tipis
    early_signals.sort(key=lambda x: x['top_5_sell_idr'])

    output_data = {
        'btc_status': {
            'is_correcting': True
        },
        'updated_at': get_wib_time(),
        'total_signals': len(early_signals),
        'signals': early_signals[:10]
    }

    # HANYA DISIMPAN KE signals.json
    with open('signals.json', 'w') as f:
        json.dump(output_data, f, indent=4)

    print(f"[SUCCESS] Selesai pada {get_wib_time()}. Ditemukan {len(early_signals)} koin potensial.")

if __name__ == "__main__":
    run_ultra_early_scanner()
