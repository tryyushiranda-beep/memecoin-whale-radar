import requests
import json
from datetime import datetime, timedelta

INDODAX_TRADES_URL = "https://indodax.com/api/trades/"
INDODAX_SUMMARIES_URL = "https://indodax.com/api/summaries"
INDODAX_DEPTH_URL = "https://indodax.com/api/depth/"

HEAVY_COINS = ['BTC', 'ETH', 'USDT', 'USDC', 'BNB', 'SOL', 'XRP', 'TRX', 'DOGE', 'ADA', 'MATIC']

def get_wib_time():
    wib_now = datetime.utcnow() + timedelta(hours=7)
    return wib_now.strftime("%d %b %Y - %H:%M:%S WIB")

def get_market_data():
    try:
        res = requests.get(INDODAX_SUMMARIES_URL, timeout=10)
        if res.status_code == 200:
            return res.json().get('tickers', {})
    except Exception as e:
        print(f"[ERROR] Summaries gagal: {e}")
    return {}

def check_btc_correcting():
    """
    ANALISIS KOREKSI BTC REAL-TIME
    Memeriksa kedalaman Order Book & Perubahan Harga 24 Jam
    """
    # 1. CEK DENGAN KEDALAMAN ORDER BOOK
    try:
        res = requests.get(f"{INDODAX_DEPTH_URL}btc_idr", timeout=5)
        if res.status_code == 200:
            data = res.json()
            sell_orders = data.get('sell', [])
            buy_orders = data.get('buy', [])
            
            tot_sell_idr = 0
            tot_buy_idr = 0

            # Hitung antrean Jual
            for item in sell_orders[:30]:
                val1 = float(item[0])
                val2 = float(item[1])
                # Antisipasi pembalikan posisi harga/jumlah dari API
                tot_sell_idr += (val1 * val2) if (val1 > 100_000 or val2 > 100_000) else val1

            # Hitung antrean Beli
            for item in buy_orders[:30]:
                val1 = float(item[0])
                val2 = float(item[1])
                tot_buy_idr += (val1 * val2) if (val1 > 100_000 or val2 > 100_000) else val1

            grand_total = tot_sell_idr + tot_buy_idr
            if grand_total > 0:
                sell_pct = (tot_sell_idr / grand_total) * 100
                print(f"[DEBUG BTC] Persentase Tekanan Jual: {sell_pct:.1f}%")
                
                # Asal antrean Jual > Beli (>= 50.1%), langsung deteksi KOREKSI
                if sell_pct >= 50.1:
                    return True
    except Exception as e:
        print(f"[ERROR] Cek Depth BTC gagal: {e}")

    # 2. BACKUP: CEK PERUBAHAN HARGA HARI INI
    try:
        tickers = get_market_data()
        btc_data = tickers.get('btc_idr', {})
        last_price = float(btc_data.get('last', 0))
        high_price = float(btc_data.get('high', 0))
        
        if high_price > 0:
            drop_pct = ((high_price - last_price) / high_price) * 100
            if drop_pct >= 0.5:  # Jika harga BTC turun >= 0.5% dari harga tertinggi hari ini
                return True
    except Exception:
        pass

    # KETENTUAN UTAMA: Buka radar selama ada tekanan jual di aplikasi Indodax
    return True

def get_real_whale_buys(pair_id):
    try:
        url = f"{INDODAX_TRADES_URL}{pair_id}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            trades = res.json()
            
            total_real_buy_idr = 0
            total_real_sell_idr = 0
            whale_transactions_count = 0

            for t in trades[:50]:
                price = float(t.get('price', 0))
                amount = float(t.get('amount', 0))
                trade_type = t.get('type', '')
                idr_val = price * amount

                if trade_type == 'buy':
                    total_real_buy_idr += idr_val
                    if idr_val >= 10_000_000:
                        whale_transactions_count += 1
                elif trade_type == 'sell':
                    total_real_sell_idr += idr_val

            grand_total = total_real_buy_idr + total_real_sell_idr
            if grand_total > 0:
                real_buy_pct = round((total_real_buy_idr / grand_total) * 100, 1)
                return real_buy_pct, round(total_real_buy_idr), whale_transactions_count
    except Exception:
        pass
    return 0, 0, 0

def run_decoupling_radar():
    tickers = get_market_data()
    if not tickers:
        print("[ERROR] Ticker kosong.")
        return

    btc_is_correcting = check_btc_correcting()
    anomalies = []

    if btc_is_correcting:
        print("[INFO] BTC Koreksi Terdeteksi. Memindai Haka Paus...")

        for pair_id, data in tickers.items():
            if not pair_id.endswith('_idr'):
                continue
            
            symbol = pair_id.replace('_idr', '').upper()
            if symbol in HEAVY_COINS:
                continue

            try:
                vol_idr = float(data.get('vol_idr', 0))
                last_price = float(data.get('last', 0))
                high_price = float(data.get('high', 0))

                if vol_idr < 30_000_000 or last_price <= 0:
                    continue

                discount_pct = round(((high_price - last_price) / high_price) * 100, 1) if high_price > 0 else 0
                real_buy_pct, real_buy_volume, whale_tx_count = get_real_whale_buys(pair_id)

                if real_buy_pct >= 65.0 and whale_tx_count >= 1:
                    status_tag = f"🐋 {whale_tx_count}x HAKA PAUS (>=10M)"

                    anomalies.append({
                        'symbol': symbol,
                        'price_idr': last_price,
                        'discount_pct': discount_pct,
                        'real_buy_pct': real_buy_pct,
                        'real_buy_volume': real_buy_volume,
                        'whale_tx_count': whale_tx_count,
                        'vol_24h_idr': round(vol_idr),
                        'status_tag': status_tag,
                        'trade_url': f"https://indodax.com/market/{pair_id}",
                        'timestamp': get_wib_time()
                    })
            except Exception:
                continue

        anomalies.sort(key=lambda x: (x['whale_tx_count'], x['real_buy_pct']), reverse=True)

    output_data = {
        'btc_status': {
            'is_correcting': btc_is_correcting
        },
        'updated_at': get_wib_time(),
        'signals': anomalies[:10]
    }

    with open('decoupling_signals.json', 'w') as f:
        json.dump(output_data, f, indent=4)

    with open('signals.json', 'w') as f:
        json.dump(output_data, f, indent=4)

    print(f"[SUCCESS] Selesai pada {get_wib_time()}")

if __name__ == "__main__":
    run_decoupling_radar()
