import requests
import json
from datetime import datetime, timedelta, timezone

INDODAX_TRADES_URL = "https://indodax.com/api/trades/"
INDODAX_SUMMARIES_URL = "https://indodax.com/api/summaries"
INDODAX_DEPTH_URL = "https://indodax.com/api/depth/"

HEAVY_COINS = ['BTC', 'ETH', 'USDT', 'USDC', 'BNB', 'SOL', 'XRP', 'TRX', 'DOGE', 'ADA', 'MATIC']

def get_wib_time():
    """Mendapatkan jam WIB (UTC+7) secara akurat tanpa terpengaruh jam server GitHub"""
    wib = timezone(timedelta(hours=7))
    return datetime.now(wib).strftime("%d %b %Y - %H:%M:%S WIB")

def get_market_data():
    try:
        res = requests.get(INDODAX_SUMMARIES_URL, timeout=10)
        if res.status_code == 200:
            return res.json().get('tickers', {})
    except Exception as e:
        print(f"[ERROR] Gagal ambil summaries: {e}")
    return {}

def check_btc_correcting():
    """
    ANALISIS KEDALAMAN ORDER BOOK BTC AKURAT
    Membaca 50 antrean Jual vs Beli untuk mencerminkan indikator di aplikasi Indodax.
    """
    try:
        res = requests.get(f"{INDODAX_DEPTH_URL}btc_idr", timeout=5)
        if res.status_code == 200:
            data = res.json()
            sell_orders = data.get('sell', [])
            buy_orders = data.get('buy', [])
            
            # Hitung kedalaman hingga 50 antrean agar presisi seperti di app Indodax
            tot_sell_idr = sum(float(i[0]) * float(i[1]) for i in sell_orders[:50])
            tot_buy_idr = sum(float(i[0]) * float(i[1]) for i in buy_orders[:50])
            
            grand_total = tot_sell_idr + tot_buy_idr
            if grand_total > 0:
                sell_pct = (tot_sell_idr / grand_total) * 100
                print(f"[DEBUG BTC] Tekanan Jual: {sell_pct:.1f}% | Beli: {100-sell_pct:.1f}%")
                # Koreksi dianggap valid jika tekanan jual >= 51.5%
                return sell_pct >= 51.5
    except Exception as e:
        print(f"[ERROR] Cek BTC gagal: {e}")
    return False

def get_real_whale_buys(pair_id):
    """ANALISIS HAKA PAUS >= RP 10 JUTA"""
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
        print("[ERROR] Ticker data kosong.")
        return

    btc_is_correcting = check_btc_correcting()
    anomalies = []

    if btc_is_correcting:
        print("[INFO] BTC Koreksi Terdeteksi. Memindai Haka Paus >= Rp 10 Juta...")

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

    # Simpan ke kedua file JSON agar dasbor versi mana pun tetap sinkron
    with open('decoupling_signals.json', 'w') as f:
        json.dump(output_data, f, indent=4)

    with open('signals.json', 'w') as f:
        json.dump(output_data, f, indent=4)

    print(f"[SUCCESS] Selesai. Ditemukan {len(anomalies)} koin dengan HAKA Paus >= Rp 10 Juta!")

if __name__ == "__main__":
    run_decoupling_radar()
