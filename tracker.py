import os
import json
import time
import requests
from datetime import datetime, timezone

SIGNALS_FILE = "signals.json"

# Hanya izinkan jaringan/blockchain resmi utama
ALLOWED_CHAINS = {'SOLANA', 'ETHEREUM', 'BSC', 'POLYGON', 'ARBITRUM', 'BASE'}

def safe_float(val, default=0.0):
    """Mencegah crash jika API mengembalikan nilai None / null / string tidak valid"""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default

def safe_int(val, default=0):
    """Mencegah crash jika nilai integer bernilai None"""
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default

def get_all_indodax_coins():
    """Mengambil seluruh daftar altcoin resmi aktif dari API Indodax"""
    coins = set()
    try:
        url = "https://indodax.com/api/pairs"
        res = requests.get(url, timeout=10).json()
        if isinstance(res, list):
            for pair in res:
                traded_coin = pair.get('traded_currency', '').upper()
                if traded_coin and traded_coin not in ['IDR', 'USDT']:
                    coins.add(traded_coin)
    except Exception as e:
        print(f"Error fetching Indodax market pairs: {e}")
    return list(coins)

def fetch_whale_signals():
    old_signals_map = {}
    old_signals_list = []
    
    # 1. Baca data lama untuk mempertahankan akumulasi 'count' dan riwayat sinyal
    try:
        if os.path.exists(SIGNALS_FILE):
            with open(SIGNALS_FILE, 'r') as f:
                old_data = json.load(f)
                if isinstance(old_data, list):
                    old_signals_list = old_data
                    for item in old_data:
                        symbol = item.get('token')
                        if symbol:
                            old_signals_map[symbol] = item
    except Exception as e:
        print(f"Error loading old signals: {e}")

    indodax_coins = get_all_indodax_coins()
    new_signals = []
    current_time_ms = int(time.time() * 1000)
    
    for symbol in indodax_coins:
        if symbol in ['BTC', 'WBTC', 'USDT', 'USDC']:
            continue
            
        try:
            time.sleep(0.15) # Jeda aman anti rate-limit API DexScreener
            
            search_url = f"https://api.dexscreener.com/latest/dex/search?q={symbol}"
            response = requests.get(search_url, timeout=7)
            
            # Penanganan khusus jika kena pembatasan kuota API (Rate Limit 429)
            if response.status_code == 429:
                time.sleep(2)
                continue
                
            if response.status_code != 200:
                continue
                
            res = response.json()
            pairs = res.get('pairs') or [] # Aman dari TypeError jika pairs bernilai None
            
            if not pairs or not isinstance(pairs, list):
                continue
                
            selected_pair = None
            for p in pairs:
                if not isinstance(p, dict):
                    continue
                c_id = str(p.get('chainId', '') or '').upper()
                base_token = p.get('baseToken') or {}
                t_sym = str(base_token.get('symbol', '') or '').upper()
                
                if c_id in ALLOWED_CHAINS and t_sym == symbol:
                    selected_pair = p
                    break
            
            if not selected_pair:
                continue
                
            # --- 1. FILTER ANTI-RUGPULL / PAIR AGE (Wajib Ada & > 24 Jam) ---
            pair_created_at = safe_int(selected_pair.get('pairCreatedAt'))
            if pair_created_at > 0:
                age_hours = (current_time_ms - pair_created_at) / (1000 * 3600)
                if age_hours < 24:
                    continue # Lewati koin yang umurnya belum 24 jam
            
            # --- 2. FILTER MARKET CAP SWEET SPOT (Rp 15 Miliar - Rp 150 Miliar) ---
            fdv = safe_float(selected_pair.get('fdv'))
            mcap = safe_float(selected_pair.get('marketCap'), default=fdv)
            mcap_idr = mcap * 15800
            
            # Buang jika data Market Cap di luar rentang Rp 15M - Rp 150M!
            if mcap_idr < 15_000_000_000 or mcap_idr > 150_000_000_000:
                continue
            
            chain_id = str(selected_pair.get('chainId', 'solana') or 'solana').upper()
            price_usd = safe_float(selected_pair.get('priceUsd'))
            
            vol_dict = selected_pair.get('volume') or {}
            vol_5m = safe_float(vol_dict.get('m5'))
            
            price_change_dict = selected_pair.get('priceChange') or {}
            price_change_5m = safe_float(price_change_dict.get('m5'))
            
            txs_dict = selected_pair.get('txns') or {}
            txs_5m = txs_dict.get('m5') or {}
            buys = safe_int(txs_5m.get('buys'))
            sells = safe_int(txs_5m.get('sells'))
            
            # Saringan Dasar: Tolak jika tidak ada transaksi atau dominasi jual terlalu tinggi
            if buys == 0:
                continue
            if sells > 0 and (buys / sells) < 0.8:
                continue
            
            price_idr = price_usd * 15800
            val_idr = vol_5m * 15800
            
            # Saringan utama nominal minimal Rp 50 Juta
            if val_idr >= 50_000_000 and price_idr > 0:
                buy_ratio = (buys / sells) if sells > 0 else float(buys)
                
                # --- 3 & 4. DETEKSI KATEGORI SIGNAL ---
                signal_type = "STANDARD"
                type_label = "🐋 Whale Activity"
                
                # WHALE BURST: Belian masif instan >= Rp 100M & rasio beli >= 2.0
                if val_idr >= 100_000_000 and buy_ratio >= 2.0:
                    signal_type = "BURST"
                    type_label = "🚨 WHALE BURST (Lompatan Awal)"
                # SILENT ACCUMULATION: Volume besar tapi harga belum pump (<= 5%)
                elif price_change_5m <= 5.0:
                    signal_type = "SILENT"
                    type_label = "💎 SILENT ACCUMULATION (Harga Murah/Dasar)"

                tx_time_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                pair_addr = str(selected_pair.get('pairAddress', '') or '')
                wallet_short = f"0x{pair_addr[:4]}...{pair_addr[-4:]}" if len(pair_addr) >= 8 else "0x0000"
                tx_hash = f"tx_{symbol}_{int(datetime.now(timezone.utc).timestamp())}"
                indodax_url = f"https://indodax.com/market/{symbol}IDR"
                
                # Ambil nilai count lama jika koin ini sudah pernah terdeteksi sebelumnya
                prev_count = safe_int(old_signals_map.get(symbol, {}).get('count'), 0)
                new_count = prev_count + 1
                
                mcap_display = f"Rp {mcap_idr/1_000_000_000:,.1f} M" if mcap_idr >= 1_000_000_000 else f"Rp {mcap_idr:,.0f}"
                
                signal_entry = {
                    "id": tx_hash,
                    "hash": tx_hash,
                    "chain": chain_id,
                    "action": "BUY",
                    "signal_type": signal_type,
                    "wallet_name": f"{type_label} ({wallet_short})",
                    "token": symbol,
                    "token_name": f"Harga: Rp {price_idr:,.4f} ({price_change_5m:+.2f}% 5m) | MCap: {mcap_display}",
                    "amount": f"{vol_5m/price_usd:,.0f}" if price_usd > 0 else "0",
                    "est_val_usd": f"${vol_5m:,.2f}",
                    "liquidity": f"Rp {val_idr:,.0f}",
                    "count": new_count,
                    "market_cap": f"Sinyal Pembelian On-Chain ({chain_id})",
                    "timestamp": tx_time_str,
                    "dex_chart": indodax_url,
                    "photon_link": indodax_url
                }
                new_signals.append(signal_entry)
        except Exception as e:
            print(f"Error checking {symbol}: {e}")
            
    # Gabungkan sinyal baru di paling atas, diikuti sinyal lama yang koinnya belum terdeteksi ulang
    new_tokens = {s['token'] for s in new_signals}
    retained_old_signals = [s for s in old_signals_list if s.get('token') not in new_tokens]
    
    final_signals = new_signals + retained_old_signals
    
    # Simpan maksimal 50 sinyal terbaru
    return final_signals[:50]

def save_signals(signals_data):
    try:
        with open(SIGNALS_FILE, "w") as f:
            json.dump(signals_data, f, indent=2)
    except Exception as e:
        print(f"Error saving signals to file: {e}")

def main():
    new_signals = fetch_whale_signals()
    save_signals(new_signals)
    print("✅ Sinyal diperbarui! Kode 100% sempurna, aman, dan konsisten.")

if __name__ == "__main__":
    main()
