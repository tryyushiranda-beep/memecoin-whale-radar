import requests
import time
import json

# Mengabaikan koin raksasa & stablecoin (Fokus Altcoin Kecil & Memecoin)
HEAVY_COINS = ['BTC', 'ETH', 'USDT', 'USDC', 'BNB', 'SOL', 'XRP', 'TRX', 'DOGE', 'MATIC', 'ADA', 'DOT']

INDODAX_SUMMARIES_URL = "https://indodax.com/api/summaries"
DEX_SEARCH_URL = "https://api.dexscreener.com/latest/dex/search?q="

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
}

def get_indodax_altcoins():
    try:
        res = requests.get(INDODAX_SUMMARIES_URL, headers=HEADERS, timeout=10)
        if res.status_code != 200:
            return []

        tickers = res.json().get('tickers', {})
        candidates = []

        for pair_id, data in tickers.items():
            if not pair_id.endswith('_idr'):
                continue

            symbol = pair_id.replace('_idr', '').upper()
            if symbol in HEAVY_COINS:
                continue

            try:
                last_price = float(data.get('last', 0))
                vol_idr = float(data.get('vol_idr', 0))
                high_24h = float(data.get('high', 0))

                # Filter Altcoin/Memecoin Aktif (Volume Rp 50 Juta - Rp 5 Miliar)
                if last_price > 0 and 50_000_000 <= vol_idr <= 5_000_000_000:
                    candidates.append({
                        'symbol': symbol,
                        'price_idr': last_price,
                        'high_24h_idr': high_24h,
                        'vol_24h_idr': vol_idr
                    })
            except Exception:
                continue

        return candidates
    except Exception as e:
        print(f"[ERROR] Fetching Indodax Data: {e}")
        return []

def evaluate_multi_layer_smart_money(symbol):
    """
    Multi-Layer Smart Money Filter:
    - Net Buy Ratio (>65%)
    - Volume Explosion (>15% dari MC/Volume 1h)
    - Golden Signal Classification
    """
    try:
        url = f"{DEX_SEARCH_URL}{symbol}"
        res = requests.get(url, headers=HEADERS, timeout=5)
        if res.status_code == 200:
            pairs = res.json().get('pairs', [])
            if pairs:
                main_pair = pairs[0]
                buys_h1 = main_pair.get('txns', {}).get('h1', {}).get('buys', 0)
                sells_h1 = main_pair.get('txns', {}).get('h1', {}).get('sells', 0)
                vol_h1 = float(main_pair.get('volume', {}).get('h1', 0))
                mcap = float(main_pair.get('fdv', 0) or main_pair.get('marketCap', 0))
                
                total_tx = buys_h1 + sells_h1
                buy_ratio = round((buys_h1 / total_tx) * 100) if total_tx > 0 else 50
                chain = main_pair.get('chainId', 'unknown').upper()

                # Cek kriteria Volume Explosion
                vol_explosion = False
                if mcap > 0 and (vol_h1 / mcap) >= 0.15:
                    vol_explosion = True

                # Tentukan Status Sinyal
                if buy_ratio >= 65 and vol_explosion:
                    signal_type = "GOLDEN SIGNAL"
                    signal_score = buy_ratio + 30
                elif buy_ratio >= 60:
                    signal_type = "HIGH MOMENTUM"
                    signal_score = buy_ratio + 10
                else:
                    signal_type = "NORMAL"
                    signal_score = buy_ratio

                return buy_ratio, chain, signal_type, signal_score, vol_h1
    except Exception:
        pass
    return 50, "INDODAX", "NORMAL", 50, 0

def run_scanner():
    print("==================================================")
    print("  INDODAX SMART MONEY RADAR (BEVAN 2.0 FILTER)    ")
    print("==================================================")

    altcoins = get_indodax_altcoins()
    valid_signals = []

    for coin in altcoins:
        symbol = coin['symbol']
        buy_ratio, chain, signal_type, signal_score, vol_h1 = evaluate_multi_layer_smart_money(symbol)

        # Hitung persentase diskon dari harga tertinggi harian
        discount_pct = ((coin['high_24h_idr'] - coin['price_idr']) / coin['high_24h_idr']) * 100 if coin['high_24h_idr'] > 0 else 0

        valid_signals.append({
            'symbol': symbol,
            'chain': chain,
            'price_idr': coin['price_idr'],
            'high_24h_idr': coin['high_24h_idr'],
            'vol_24h_idr': round(coin['vol_24h_idr']),
            'discount_pct': round(discount_pct, 1),
            'buy_ratio': buy_ratio,
            'signal_type': signal_type,
            'signal_score': signal_score,
            'trade_url': f"https://indodax.com/market/{symbol.lower()}idr",
            'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
        })

    # Urutkan berdasarkan Skor Sinyal Tertinggi
    valid_signals.sort(key=lambda x: (x['signal_score'], x['discount_pct']), reverse=True)
    final_signals = valid_signals[:15]

    with open('signals.json', 'w') as f:
        json.dump(final_signals, f, indent=4)

    print(f"Selesai! {len(final_signals)} altcoin/memecoin Indodax tersimpan di signals.json.")

if __name__ == "__main__":
    run_scanner()
