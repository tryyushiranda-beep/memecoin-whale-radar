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

                # Filter Volume 24h Indodax Rp 50 Juta s/d Rp 500 Juta (Micro-Cap Focus)
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

def find_best_matching_pair(pairs, target_symbol):
    valid_pairs = []
    for pair in pairs[:12]:
        base_token = pair.get('baseToken', {}).get('symbol', '').upper()
        liquidity_usd = float(pair.get('liquidity', {}).get('usd', 0))
        
        if base_token != target_symbol or liquidity_usd < 2000:
            continue
            
        valid_pairs.append((liquidity_usd, pair))
        
    if not valid_pairs:
        return None
        
    valid_pairs.sort(key=lambda x: x[0], reverse=True)
    return valid_pairs[0][1]

def check_gmgn_whale_activity(chain, token_address):
    """
    INSPEKSI GMGN API (MURNI PER-WALLET BUY):
    Memeriksa pembeli teratas di GMGN.
    Transaksi JUAL diabaikan total, hanya menghitung total_buy_usd >= $1,000 dalam 15 menit.
    """
    chain_map = {'SOLANA': 'sol', 'ETH': 'eth', 'BSC': 'bsc', 'BASE': 'base', 'ARBITRUM': 'arb'}
    chain_code = chain_map.get(chain.upper(), 'sol')
    
    try:
        url = f"https://gmgn.ai/defi/quotation/v1/tokens/top_buyers/{chain_code}/{token_address}"
        res = session.get(url, headers=get_random_headers(), timeout=4)
        
        if res.status_code == 200:
            data = res.json().get('data', [])
            current_time = time.time()
            
            for buyer in data[:10]:
                last_active = float(buyer.get('last_active_timestamp', 0))
                buy_amount_usd = float(buyer.get('total_buy_usd', 0))
                
                # Memastikan transaksi BUY per-wallet masif >= $1,000 USD dalam 15 menit (900 detik)
                if (current_time - last_active <= 900) and buy_amount_usd >= 1000:
                    return True, round(buy_amount_usd)
    except Exception:
        pass
    return False, 0

def check_dexscreener_whale_tx(chain, pair_address):
    """
    INSPEKSI DEXSCREENER API (MURNI BUY VOLUME INFLOW):
    Memeriksa volume Beli 5-15 menit terakhir.
    """
    try:
        url = f"https://api.dexscreener.com/latest/dex/pairs/{chain.lower()}/{pair_address}"
        res = session.get(url, headers=get_random_headers(), timeout=5)
        
        if res.status_code == 200:
            pair_data = res.json().get('pair', {})
            m5_vol_buy = float(pair_data.get('volume', {}).get('m5', 0))
            m5_buys_count = float(pair_data.get('txns', {}).get('m5', {}).get('buys', 0))
            
            if m5_buys_count > 0:
                avg_tx_size = m5_vol_buy / m5_buys_count
                if m5_vol_buy >= 1000 or avg_tx_size >= 500:
                    return True, round(m5_vol_buy)
    except Exception:
        pass
    return False, 0

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
                sells_h1 = float(main_pair.get('txns', {}).get('h1', {}).get('sells', 0))
                vol_h1 = float(main_pair.get('volume', {}).get('h1', 0))
                mcap = float(main_pair.get('fdv', 0) or main_pair.get('marketCap', 0))
                chain = main_pair.get('chainId', 'unknown').upper()
                token_address = main_pair.get('baseToken', {}).get('address', '')
                pair_address = main_pair.get('pairAddress', '')
                
                # 1. Filter Market Cap Maksimal $5,000,000 USD (Hanya Micro-Cap)
                if mcap > 5_000_000:
                    return None

                # 2. VERIFIKASI DUAL WHALE BUY (Murni Pembelian Paus >= $1,000 USD)
                gmgn_has_whale, gmgn_val = check_gmgn_whale_activity(chain, token_address)
                dex_has_whale, dex_val = check_dexscreener_whale_tx(chain, pair_address)
                
                # WAJIB LOLOS SALAH SATU ATAU KEDUANYA
                if not (gmgn_has_whale or dex_has_whale):
                    return None  # Abaikan jika tidak ada transaksi Beli Paus $1,000+ dalam 15 menit

                whale_inflow_val = max(gmgn_val, dex_val)
                total_tx = buys_h1 + sells_h1
                buy_ratio = round((buys_h1 / total_tx) * 100) if total_tx > 0 else 50
                buy_ratio = min(max(buy_ratio, 0), 100)

                discount_pct = ((coin['high_24h_idr'] - coin['price_idr']) / coin['high_24h_idr']) * 100 if coin['high_24h_idr'] > 0 else 0

                source_label = "GMGN + DEX" if (gmgn_has_whale and dex_has_whale) else ("GMGN" if gmgn_has_whale else "DEX")
                freshness_status = f"🚨 WHALE BUY (${whale_inflow_val} via {source_label} <15m)"

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
                    'signal_type': "SUPER GOLDEN SIGNAL",
                    'signal_score': buy_ratio + 35,
                    'trade_url': f"https://indodax.com/market/{symbol.lower()}idr",
                    'tracker_url': tracker_url,
                    'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
                }
    except Exception:
        pass
    return None

def run_scanner():
    print("==================================================")
    print("  INDODAX RADAR v6.7 (AUTO DUAL WHALE BUY FILTER) ")
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

    print(f"Selesai! {len(final_signals)} koin terkonfirmasi transaksi Paus BUY tersimpan.")

if __name__ == "__main__":
    run_scanner()
