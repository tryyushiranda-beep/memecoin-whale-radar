import requests
import json
import time

INDODAX_TRADES_URL = "https://indodax.com/api/trades/"
INDODAX_SUMMARIES_URL = "https://indodax.com/api/summaries"
INDODAX_DEPTH_URL = "https://indodax.com/api/depth/"

HEAVY_COINS = ['BTC', 'ETH', 'USDT', 'USDC', 'BNB', 'SOL', 'XRP', 'TRX', 'DOGE', 'ADA', 'MATIC']

def get_market_data():
    try:
        res = requests.get(INDODAX_SUMMARIES_URL, timeout=10)
        if res.status_code == 200:
            return res.json().get('tickers', {})
    except Exception as e:
        print(f"[ERROR] Gagal ambil summaries: {e}")
    return {}

def check_btc_correcting():
    """Cek apakah BTC sedang tertekan/koreksi di Order Book"""
    try:
        res = requests.get(f"{INDODAX_DEPTH_URL}btc_idr", timeout=5)
        if res.status_code == 200:
            data = res.json()
            sell_orders = data.get('sell', [])
            buy_orders = data.get('buy', [])
            
            tot_sell = sum(float(i[0]) * float(i[1]) for i in sell_orders[:10])
            tot_buy = sum(float(i[0]) * float(i[1]) for i in buy_orders[:10])
            
            if (tot_sell + tot_buy) > 0:
                sell_pct = (tot_sell / (tot_sell + tot_buy)) * 100
                return sell_pct >= 51.5
    except Exception:
        pass
    return False

def get_real_whale_buys(pair_id):
    """
    ANALISIS TRANSAKSI EKSEKUSI RIIL (MARKET BUY / HAKA)
    Hanya menghitung transaksi Beli bernilai MINIMAL Rp 10 JUTA sekali klik.
    """
    try:
        url = f"{INDODAX_TRADES_URL}{pair_id}"
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            trades = res.json()
            
            total_real_buy_idr = 0
            total_real_sell_idr = 0
            whale_transactions_count = 0

            # Cek 50 transaksi eksekusi terakhir
            for t in trades[:50]:
                price = float(t.get('price', 0))
                amount = float(t.get('amount', 0))
                trade_type = t.get('type', '')
                idr_val = price * amount

                if trade_type == 'buy':
                    total_real_buy_idr += idr_val
                    # SYARAT BARU: HANYA DAHULUKAN TRANSAKSI HAKA >= RP 10 JUTA
                    if idr_val >= 10_000_000:
                        whale_transactions_count += 1
                elif trade_type == 'sell':
                    total_real_sell_idr += idr_val

            grand_total = total_real_buy_idr + total_real_sell_idr
            if grand_total > 0:
                real_buy_pct = round((total_buy_idr / grand_total) * 100, 1) if 'total_buy_idr' in locals() else round((total_real_buy_idr / grand_total) * 100, 1)
                return real_buy_pct, round(total_real_buy_idr), whale_transactions_count
    except Exception:
        pass
    return 0, 0, 0

def run_decoupling_radar():
    tickers = get_market_data()
    if not tickers:
        print("[ERROR] Ticker data kosong.")
        return

    btc_is_correcting = check_btc_correcting()
    anomalies = []

    if btc_is_correcting:
        print("[INFO] BTC Koreksi Terdeteksi. Memindai Eksekusi Haka Paus >= Rp 10 Juta...")

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

                # Dapatkan transaksi Beli Riil (Filter Rp 10 Juta)
                real_buy_pct, real_buy_volume, whale_tx_count = get_real_whale_buys(pair_id)

                # KLASIFIKASI SINYAL PAUS:
                # 1. Total Eksekusi Beli Riil >= 65%
                # 2. Ada MINIMAL 1x transaksi Haka langsung >= Rp 10 Juta
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
                        'timestamp': time.strftime("%H:%M:%S WIB")
                    })
            except Exception:
                continue

        # Urutkan berdasarkan frekuensi transaksi Rp 10 Juta terbanyak
        anomalies.sort(key=lambda x: (x['whale_tx_count'], x['real_buy_pct']), reverse=True)

    # Simpan Output ke file JSON
    output_data = {
        'btc_status': {
            'is_correcting': btc_is_correcting
        },
        'updated_at': time.strftime("%d %b %Y - %H:%M:%S WIB"),
        'signals': anomalies[:10]
    }

    with open('decoupling_signals.json', 'w') as f:
        json.dump(output_data, f, indent=4)

    print(f"[SUCCESS] Pindaian selesai. Ditemukan {len(anomalies)} koin dengan HAKA Paus >= Rp 10 Juta!")

if __name__ == "__main__":
    run_decoupling_radar()
