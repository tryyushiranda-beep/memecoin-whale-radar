import requests
import json
import time
from datetime import datetime, timezone

# ==========================================
# KONFIGURASI PARAMETER AWAL (SUPER SELEKTIF)
# ==========================================
IDR_PER_USD = 15500              # Kurs perkiraan USD ke IDR
MIN_PAIR_AGE_HOURS = 24          # Anti-Rugpull: Umur pair minimal 24 jam
MIN_MCAP_IDR = 15_000_000_000     # Minimum MCap Sweet Spot: Rp 15 Miliar
MAX_MCAP_IDR = 150_000_000_000    # Maksimum MCap Sweet Spot: Rp 150 Miliar
MIN_BUY_VOL_5M_IDR = 50_000_000   # Minimum Volume Beli 5 Menit: Rp 50 Juta

SIGNALS_FILE = "signals.json"
MAX_SIGNALS_HISTORY = 50

# Blockchain resmi & kredibel untuk menghindari fake/junk token
ALLOWED_CHAINS = {'SOLANA', 'ETHEREUM', 'BSC', 'POLYGON', 'ARBITRUM', 'BASE', 'AVALANCHE'}

def safe_float(val, default=0.0):
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default

def safe_int(val, default=0):
    try:
        return int(val) if val is not None else default
    except (ValueError, TypeError):
        return default

def get_indodax_prices_and_pairs():
    """
    Mengambil daftar koin Indodax beserta HARGA ASLI REAL-TIME langsung dari API Indodax
    """
    url_pairs = "https://indodax.com/api/pairs"
    url_ticker = "https://indodax.com/api/ticker_all"
    
    indodax_data = {}
    
    try:
        # 1. Ambil data Ticker Harga Indodax
        res_ticker = requests.get(url_ticker, timeout=10)
        tickers = {}
        if res_ticker.status_code == 200:
            tickers = res_ticker.json().get('tickers', {})

        # 2. Ambil daftar pairs
        res_pairs = requests.get(url_pairs, timeout=10)
        if res_pairs.status_code == 200:
            data = res_pairs.json()
            items = data if isinstance(data, list) else data.values() if isinstance(data, dict) else []
            
            for item in items:
                if not isinstance(item, dict):
                    continue
                traded = str(item.get('traded_currency', '') or '').upper()
                base = str(item.get('base_currency', '') or '').upper()
                token_symbol = traded if traded else base
                
                if token_symbol and token_symbol not in ['IDR', 'USDT', 'BTC', 'WBTC']:
                    # Ambil harga last dari ticker Indodax
                    pair_key = f"{token_symbol.lower()}_idr"
                    ticker_info = tickers.get(pair_key, {})
                    last_price_indodax = safe_float(ticker_info.get('last', 0))
                    
                    indodax_data[token_symbol] = {
                        "price_indodax": last_price_indodax
                    }
    except Exception as e:
        print(f"Error fetching Indodax data: {e}")
        
    return indodax_data

def scan_dexscreener_exact(token_symbol):
    url = f"https://api.dexscreener.com/latest/dex/search?q={token_symbol}"
    
    try:
        res = requests.get(url, timeout=10)
        if res.status_code == 429:
            print("Rate limited by DexScreener, sleeping 2s...")
            time.sleep(2)
            return None
        if res.status_code == 200:
            data = res.json()
            pairs = data.get('pairs') or []
            if not isinstance(pairs, list):
                return None
            
            best_pair = None
            max_liq = -1
            
            for p in pairs:
                if not isinstance(p, dict):
                    continue
                
                chain_id = str(p.get('chainId', '') or '').upper()
                base_token = p.get('baseToken') or {}
                base_sym = str(base_token.get('symbol', '') or '').upper()
                
                if base_sym == token_symbol and chain_id in ALLOWED_CHAINS:
                    liq = safe_float((p.get('liquidity') or {}).get('usd', 0))
                    if liq > max_liq:
                        max_liq = liq
                        best_pair = p
            return best_pair
    except Exception as e:
        print(f"Error scanning {token_symbol}: {e}")
    return None

def analyze_whale_activity():
    indodax_dict = get_indodax_prices_and_pairs()
    print(f"Total pasangan Indodax terdeteksi: {len(indodax_dict)}")
    
    try:
        with open(SIGNALS_FILE, "r") as f:
            signals_history = json.load(f)
            if not isinstance(signals_history, list):
                signals_history = []
    except Exception:
        signals_history = []

    new_signals = []

    for token, idx_info in indodax_dict.items():
        time.sleep(0.15) # Jaga rate limit API
        
        pair_data = scan_dexscreener_exact(token)
        if not pair_data:
            continue

        # 1. Filter Umur Pair (> 24 Jam)
        created_at = safe_int(pair_data.get('pairCreatedAt', 0))
        if created_at > 0:
            age_hours = (time.time() * 1000 - created_at) / (1000 * 3600)
            if age_hours < MIN_PAIR_AGE_HOURS:
                continue

        # 2. Filter Market Cap Sweet Spot (Rp 15M - Rp 150M)
        mcap_usd = safe_float(pair_data.get('marketCap', 0))
        mcap_idr = mcap_usd * IDR_PER_USD
        if not (MIN_MCAP_IDR <= mcap_idr <= MAX_MCAP_IDR):
            continue

        # 3. Filter Volume & Inflow Beli (5 Menit)
        txns_dict = pair_data.get('txns') or {}
        txns_5m = txns_dict.get('m5') or {}
        buys_5m = safe_int(txns_5m.get('buys', 0))
        sells_5m = safe_int(txns_5m.get('sells', 0))

        vol_dict = pair_data.get('volume') or {}
        volume_5m_usd = safe_float(vol_dict.get('m5', 0))
        
        change_dict = pair_data.get('priceChange') or {}
        price_change_5m = safe_float(change_dict.get('m5', 0))

        total_txns = buys_5m + sells_5m
        buy_ratio = (buys_5m / total_txns) if total_txns > 0 else 0.5
        est_buy_vol_idr = volume_5m_usd * buy_ratio * IDR_PER_USD

        if est_buy_vol_idr < MIN_BUY_VOL_5M_IDR:
            continue

        # 4. Ambil Harga Asli Indodax (Fallback ke DexScreener jika Indodax 0)
        price_indodax = idx_info.get("price_indodax", 0)
        if price_indodax <= 0:
            price_usd = safe_float(pair_data.get('priceUsd', 0))
            price_indodax = price_usd * IDR_PER_USD

        # 5. Klasifikasi Sinyal
        chain = str(pair_data.get('chainId', 'SOLANA') or 'SOLANA').upper()
        pair_address = str(pair_data.get('pairAddress', '') or '')
        short_addr = f"({pair_address[:6]}...{pair_address[-4:]})" if len(pair_address) > 10 else ""
        
        signal_type = "SILENT"
        wallet_label = f"💎 SILENT ACCUMULATION (Harga Murah/Dasar) {short_addr}"
        
        if est_buy_vol_idr >= 100_000_000 and (price_change_5m > 5.0 or buy_ratio >= 0.7):
            signal_type = "BURST"
            wallet_label = f"🚨 WHALE BURST (Lonjakan Instan) {short_addr}"

        mcap_m_idr = mcap_idr / 1_000_000_000
        token_detail_str = f"Harga Indodax: Rp {price_indodax:,.2f} ({price_change_5m:+.2f}% 5m) | MCap: Rp {mcap_m_idr:.1f} M"
        
        current_time_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        scan_count = 1
        for old_sig in signals_history[:10]:
            if old_sig.get('token') == token:
                scan_count = safe_int(old_sig.get('count', 1)) + 1
                break

        signal_obj = {
            "token": token,
            "wallet_name": wallet_label,
            "token_name": token_detail_str,
            "liquidity": f"Rp {int(est_buy_vol_idr):,}",
            "timestamp": current_time_utc,
            "chain": chain,
            "count": scan_count,
            "signal_type": signal_type,
            "dex_chart": f"https://indodax.com/market/{token}IDR"
        }

        new_signals.append(signal_obj)

    if new_signals:
        existing_tokens = {s['token'] for s in new_signals}
        for old_s in signals_history:
            if old_s.get('token') not in existing_tokens:
                new_signals.append(old_s)
        
        final_list = new_signals[:MAX_SIGNALS_HISTORY]
        with open(SIGNALS_FILE, "w") as f:
            json.dump(final_list, f, indent=2)
        print(f"✅ Berhasil memperbarui {len(new_signals)} sinyal ke {SIGNALS_FILE}")
    else:
        print("ℹ️ Pindaian selesai. Belum ada akumulasi baru di atas Rp 50 Juta.")

if __name__ == "__main__":
    analyze_whale_activity()
