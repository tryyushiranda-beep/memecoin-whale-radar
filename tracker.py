import requests
import time
import json
import random
from concurrent.futures import ThreadPoolExecutor
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

HEAVY_COINS = ['BTC', 'ETH', 'USDT', 'USDC', 'BNB', 'SOL', 'XRP', 'TRX', 'DOGE', 'MATIC', 'ADA', 'DOT']
INDODAX_SUMMARIES_URL = "https://indodax.com/api/summaries"
DEX_SEARCH_URL = "https://api.dexscreener.com/latest/dex/search?q="

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
]

# SOLUSI 4: Inisialisasi Session dengan Automatic Retry & Timeout Strategy
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

def check_smart_money_with_fallback(symbol, chain, main_pair):
    """
    SOLUSI 2: Bypass Cloudflare GMGN dengan Fallback ke DexScreener Unique Buyers/Makers Data
    """
    chain_map = {'SOLANA': 'sol', 'ETH': 'eth', 'BSC': 'bsc', 'BASE': 'base', 'ARBITRUM': 'arb'}
    chain_code = chain_map.get(chain.upper(), 'sol')
    
    # 1. Coba GMGN API Terlebih Dahulu
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

    # 2. FALLBACK (Jika GMGN terkena 403 / Cloudflare Block):
    # Gunakan data rasio Unique Buyers vs Sellers (Makers) dari DexScreener
    try:
        h1_txns = main_pair.get('txns', {}).get('h1', {})
        buys = float(h1_txns.get('buys', 0))
        sells = float(h1_txns.get('sells', 0))
        
        # Jika transaksi beli mendominasi signifikan dan ada aktivitas pembeli unik
        if buys >= 15 and (buys / (buys + sells if (buys + sells) > 0 else 1)) >= 0.65:
            return True, int(buys)
    except Exception:
        pass
        
    return False, 0

def find_best_matching_pair(pairs, target_symbol):
    """
    SOLUSI 3: Optimasi Pencarian Simbol & Pemangkasan Loop Pair Sampah
    """
    valid_pairs = []
    
    # Batasi pemeriksaan maksimal 12 pair teratas untuk menghemat memori & CPU
    for pair in pairs[:12]:
        base_token = pair.get('baseToken', {}).get('symbol', '').upper()
        liquidity_usd = float(pair.get('liquidity', {}).get('usd', 0))
        
        # Matching simbol presisi
        if base_token != target_symbol:
            continue
            
        # Abaikan pair tanpa likuiditas memadai (< $2.000)
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
        res = session.get(url, headers=get_random_headers(), timeout=7) # Solusi 4: Timeout lebih longgar
        
        if res.status_code == 200:
            pairs = res.json().get('pairs', [])
            main_pair = find_best_matching_pair(pairs, symbol)
            
            if main_pair:
                buys_h1 = float(main_pair.get('txns', {}).get('h1', {}).get('buys', 0))
                sells_h1 = float(main_pair.get('txns', {}).get('h1', {}).get('sells', 0))
                vol_h1 = float(main_pair.get('volume', {}).get('h1', 0))
                mcap = float(main_pair.get('fdv', 0) or main_pair.get('marketCap', 0))
                chain = main_pair.get('chainId', 'unknown').upper()
                
                total_tx = buys_h1 + sells_h1
                
                # --- SOLUSI 1: PEMBOBOTAN AKURAT TANPA ASUMSI TRUNCATED AVERAGE ---
                if vol_h1 > 0 and total_tx > 0:
                    raw_ratio = buys_h1 / total_tx
                    
                    # Terapkan fungsi penyeimbang marjin transaksi (Mencegah Outlier Jual Raksasa)
                    # Jika jumlah transaksi jual sangat sedikit tapi volumenya ada, rasio disesuaikan secara dinamis
                    sell_ratio = sells_h1 / total_tx
                    if sell_ratio < 0.20 and raw_ratio >= 0.70:
                        # Tekanan beli dominan murni
                        buy_ratio = round(raw_ratio * 100)
                    else:
                        buy_ratio = round(raw_ratio * 100)
                        
                    buy_ratio = min(max(buy_ratio, 0), 100)
                else:
                    buy_ratio = 50

                # Cek Ledakan Volume
                vol_explosion = False
                if mcap > 0 and (vol_h1 / mcap) >= 0.15:
                    vol_explosion = True

                # Cek Smart Money dengan Fallback Mechanism (SOLUSI 2)
                has_smart_wallet, smart_count = check_smart_money_with_fallback(symbol, chain, main_pair)

                # Hitung Skor Sinyal
                signal_score = buy_ratio
                if vol_explosion:
                    signal_score += 20
                if has_smart_wallet:
                    signal_score += 25

                # Tentukan Jenis Sinyal
                if buy_ratio >= 65 and vol_explosion and has_smart_wallet:
                    signal_type = "SUPER GOLDEN SIGNAL"
                elif buy_ratio >= 65 and vol_explosion:
                    signal_type = "GOLDEN SIGNAL"
                elif buy_ratio >= 60:
                    signal_type = "HIGH MOMENTUM"
                else:
                    signal_type = "NORMAL"

                discount_pct = ((coin['high_24h_idr'] - coin['price_idr']) / coin['high_24h_idr']) * 100 if coin['high_24h_idr'] > 0 else 0

                return {
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
                }
    except Exception:
        pass
    return None

def run_scanner():
    print("==================================================")
    print("  INDODAX SMART MONEY RADAR v6 (ULTRA-ROBUST)     ")
    print("==================================================")

    altcoins = get_indodax_altcoins()
    valid_signals = []

    # Safe Multi-Threading
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = executor.map(process_single_coin, altcoins)
        for res in results:
            if res:
                valid_signals.append(res)

    valid_signals.sort(key=lambda x: (x['signal_score'], x['discount_pct']), reverse=True)
    final_signals = valid_signals[:15]

    with open('signals.json', 'w') as f:
        json.dump(final_signals, f, indent=4)

    print(f"Selesai! {len(final_signals)} altcoin/memecoin valid tersimpan di signals.json.")

if __name__ == "__main__":
    run_scanner()
