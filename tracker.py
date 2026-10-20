import requests
import time
import json
import random
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Mengabaikan koin berat / koin utama ber-Market Cap raksasa
HEAVY_COINS = ['BTC', 'ETH', 'USDT', 'USDC', 'BNB', 'SOL', 'XRP', 'TRX', 'DOGE', 'MATIC', 'ADA', 'DOT', 'BOME', 'PEPE', 'SHIB', 'WIF', 'BONK']
INDODAX_SUMMARIES_URL = "https://indodax.com/api/summaries"
DEX_SEARCH_URL = "https://api.dexscreener.com/latest/dex/search?q="

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
]

def create_robust_session():
    session = requests.Session()
    retries = Retry(
        total=2,
        backoff_factor=0.3,
        status_forcelist=[500, 502, 503, 504],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

session = create_robust_session()

def get_random_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'application/json'
    }

def get_indodax_altcoins():
    try:
        res = session.get(INDODAX_SUMMARIES_URL, headers=get_random_headers(), timeout=12)
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

                # Koreksi Anomali Desimal Indodax
                if high_24h > 0 and last_price > (high_24h * 10):
                    last_price = last_price / 1000

                # DIBATASI: Volume 24h Rp 50 Juta s/d Rp 500 Juta (Fokus Micro-Cap)
                if last_price > 0 and 50_000_000 <= vol_idr <= 500_000_000:
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

def check_smart_money_with_fallback(symbol, chain, main_pair):
    chain_map = {'SOLANA': 'sol', 'ETH': 'eth', 'BSC': 'bsc', 'BASE': 'base', 'ARBITRUM': 'arb'}
    chain_code = chain_map.get(chain.upper(), 'sol')
    
    try:
        time.sleep(random.uniform(0.1, 0.2))
        url = f"https://gmgn.ai/defi/quotation/v1/smartmoney/{chain_code}/wallet_activity?symbol={symbol.lower()}"
        res = session.get(url, headers=get_random_headers(), timeout=4)
        
        if res.status_code == 200:
            data = res.json()
            smart_buy_count = data.get('data', {}).get('smart_money_buy_count', 0)
            if smart_buy_count > 0:
                return True, smart_buy_count
    except Exception:
        pass

    try:
        h1_txns = main_pair.get('txns', {}).get('h1', {})
        buys = float(h1_txns.get('buys', 0))
        sells = float(h1_txns.get('sells', 0))
        
        if buys >= 15 and (buys / (buys + sells if (buys + sells) > 0 else 1)) >= 0.65:
            return True, int(buys)
    except Exception:
        pass
        
    return False, 0

def find_best_matching_pair(pairs, target_symbol):
    valid_pairs = []
    
    for pair in pairs[:12]:
        base_token = pair.get('baseToken', {}).get('symbol', '').upper()
        liquidity_usd = float(pair.get('liquidity', {}).get('usd', 0))
        
        if base_token != target_symbol:
            continue
            
        if liquidity_usd < 2000:
            continue
            
        valid_pairs.append((liquidity_usd, pair))
        
    if not valid_pairs:
        return None
        
    valid_pairs.sort(key=lambda x: x[0], reverse=True)
    return valid_pairs[0][1]

def process_single_coin(coin):
    symbol = coin['symbol']
    try:
        time.sleep(random.uniform(0.05, 0.12))
        url = f"{DEX_SEARCH_URL}{symbol}"
        res = session.get(url, headers=get_random_headers(), timeout=7)
        
        if res.status_code == 200:
            pairs = res.json().get('pairs', [])
            main_pair = find_best_matching_pair(pairs, symbol)
            
            if main_pair:
                buys_h1 = float(main_pair.get('txns', {}).get('h1', {}).get('buys', 0))
                sells_h1 = float(main_pair.get('txns', {}).get('sells', 0))
                vol_h1 = float(main_pair.get('volume', {}).get('h1', 0))
                mcap = float(main_pair.get('fdv', 0) or main_pair.get('marketCap', 0))
                chain = main_pair.get('chainId', 'unknown').upper()
                token_address = main_pair.get('baseToken', {}).get('address', '')
                pair_address = main_pair.get('pairAddress', '')
                
                # 1. FILTER MARKET CAP: Maksimal $5,000,000 USD (Hanya Micro-Cap)
                if mcap > 5_000_000:
                    return None

                # 2. FILTER FRESHNESS & MINIMAL VOLUME PAUS (1-15 MENIT TERAKHIR)
                m5_buys = float(main_pair.get('txns', {}).get('m5', {}).get('buys', 0))
                m5_vol = float(main_pair.get('volume', {}).get('m5', 0))
                h1_buys = float(main_pair.get('txns', {}).get('h1', {}).get('buys', 0))
                
                # Membuang koin jika tidak ada aktivitas transaksi beli segar dalam 5-15m
                if m5_buys < 1 and h1_buys < 4:
                    return None
                    
                # Menentukan Label Segar untuk Tampilan Dasbor
                if m5_buys >= 3 and m5_vol >= 1000:
                    freshness_status = "⚡ FRESH (<5m) | Paus Masuk"
                elif m5_buys >= 1:
                    freshness_status = "🔥 IDEAL (5-15m) | Akumulasi"
                else:
                    freshness_status = "⏱️ TOLERANSI (<15m)"

                total_tx = buys_h1 + sells_h1
                
                if vol_h1 > 0 and total_tx > 0:
                    raw_ratio = buys_h1 / total_tx
                    sell_ratio = sells_h1 / total_tx
                    if sell_ratio < 0.20 and raw_ratio >= 0.70:
                        buy_ratio = round(raw_ratio * 100)
                    else:
                        buy_ratio = round(raw_ratio * 100)
                        
                    buy_ratio = min(max(buy_ratio, 0), 100)
                else:
                    buy_ratio = 50

                vol_explosion = False
                if mcap > 0 and (vol_h1 / mcap) >= 0.15:
                    vol_explosion = True

                has_smart_wallet, smart_count = check_smart_money_with_fallback(symbol, chain, main_pair)

                signal_score = buy_ratio
                if vol_explosion:
                    signal_score += 20
                if has_smart_wallet:
                    signal_score += 25

                if buy_ratio >= 65 and vol_explosion and has_smart_wallet:
                    signal_type = "SUPER GOLDEN SIGNAL"
                elif buy_ratio >= 65 and vol_explosion:
                    signal_type = "GOLDEN SIGNAL"
                elif buy_ratio >= 60:
                    signal_type = "HIGH MOMENTUM"
                else:
                    signal_type = "NORMAL"

                discount_pct = ((coin['high_24h_idr'] - coin['price_idr']) / coin['high_24h_idr']) * 100 if coin['high_24h_idr'] > 0 else 0

                if chain == 'SOLANA':
                    tracker_url = f"https://gmgn.ai/sol/token/{token_address}" if token_address else f"https://solscan.io/token/{token_address}"
                else:
                    chain_slug = chain.lower()
                    tracker_url = f"https://dexscreener.com/{chain_slug}/{pair_address}"

                return {
                    'symbol': symbol,
                    'chain': chain,
                    'token_address': token_address,
                    'price_idr': coin['price_idr'],
                    'high_24h_idr': coin['high_24h_idr'],
                    'vol_24h_idr': round(coin['vol_24h_idr']),
                    'discount_pct': round(discount_pct, 1),
                    'buy_ratio': buy_ratio,
                    'freshness': freshness_status,
                    'signal_type': signal_type,
                    'signal_score': signal_score,
                    'trade_url': f"https://indodax.com/market/{symbol.lower()}idr",
                    'tracker_url': tracker_url,
                    'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
                }
    except Exception:
        pass
    return None

def run_scanner():
    print("==================================================")
    print("  INDODAX RADAR v6.5 (MICRO-CAP & FRESH 15m)      ")
    print("==================================================")

    altcoins = get_indodax_altcoins()
    valid_signals = []

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = executor.map(process_single_coin, altcoins)
        for res in results:
            if res:
                valid_signals.append(res)

    valid_signals.sort(key=lambda x: (x['signal_score'], x['discount_pct']), reverse=True)
    final_signals = valid_signals[:15]

    with open('signals.json', 'w') as f:
        json.dump(final_signals, f, indent=4)

    print(f"Selesai! {len(final_signals)} koin segar (1-15m) tersimpan di signals.json.")

if __name__ == "__main__":
    run_scanner()
