import os
import json
import time
import requests
from datetime import datetime, timezone

SIGNALS_FILE = "signals.json"

# Hanya izinkan jaringan/blockchain resmi utama
ALLOWED_CHAINS = {'SOLANA', 'ETHEREUM', 'BSC', 'POLYGON', 'ARBITRUM', 'BASE'}

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
    # Load data lama jika ada untuk melacak frekuensi (count)
    old_counts = {}
    try:
        if os.path.exists(SIGNALS_FILE):
            with open(SIGNALS_FILE, 'r') as f:
                old_data = json.load(f)
                if isinstance(old_data, list):
                    for item in old_data:
                        symbol = item.get('token')
                        if symbol:
                            old_counts[symbol] = item.get('count', 1)
    except Exception as e:
        print(f"Error loading old signals: {e}")

    indodax_coins = get_all_indodax_coins()
    signals = []
    
    for symbol in indodax_coins:
        if symbol in ['BTC', 'WBTC', 'USDT', 'USDC']:
            continue
            
        try:
            # Jeda mikro agar tidak memicu rate-limit API
            time.sleep(0.1)
            
            search_url = f"https://api.dexscreener.com/latest/dex/search?q={symbol}"
            res = requests.get(search_url, timeout=5).json()
            pairs = res.get('pairs', [])
            
            if not pairs:
                continue
                
            selected_pair = None
            for p in pairs:
                c_id = p.get('chainId', '').upper()
                t_sym = p.get('baseToken', {}).get('symbol', '').upper()
                if c_id in ALLOWED_CHAINS and t_sym == symbol:
                    selected_pair = p
                    break
            
            if not selected_pair:
                continue
                
            chain_id = selected_pair.get('chainId', 'solana').upper()
            price_usd = float(selected_pair.get('priceUsd', 0) or 0)
            vol_5m = float(selected_pair.get('volume', {}).get('m5', 0) or 0)
            
            # Cek Dominasi Transaksi (Beli vs Jual)
            txs_5m = selected_pair.get('txns', {}).get('m5', {})
            buys = txs_5m.get('buys', 0)
            sells = txs_5m.get('sells', 0)
            
            # Hanya loloskan jika transaksi beli lebih banyak dari jual
            if sells > 0 and (buys / sells) < 0.8:
                continue
            
            tx_time_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            
            price_idr = price_usd * 15800
            val_idr = vol_5m * 15800
            
            # Filter ketat khusus transaksi >= Rp 50.000.000
            if val_idr >= 50_000_000 and price_idr > 0:
                pair_addr = selected_pair.get('pairAddress', '')
                wallet_short = f"0x{pair_addr[:4]}...{pair_addr[-4:]}"
                tx_hash = f"tx_{symbol}_{int(datetime.now(timezone.utc).timestamp())}"
                indodax_url = f"https://indodax.com/market/{symbol}IDR"
                
                # Hitung akumulasi kemunculan (count)
                new_count = old_counts.get(symbol, 0) + 1
                
                signal_entry = {
                    "id": tx_hash,
                    "hash": tx_hash,
                    "chain": chain_id,
                    "action": "BUY",
                    "wallet_name": f"🐋 Whale ({wallet_short})",
                    "token": symbol,
                    "token_name": f"Harga On-Chain: Rp {price_idr:,.4f}" if price_idr < 10 else f"Harga On-Chain: Rp {price_idr:,.0f}",
                    "amount": f"{vol_5m/price_usd:,.0f}" if price_usd > 0 else "0",
                    "est_val_usd": f"${vol_5m:,.2f}",
                    "liquidity": f"Rp {val_idr:,.0f}",
                    "count": new_count,
                    "market_cap": f"Sinyal Pembelian On-Chain ({chain_id})",
                    "timestamp": tx_time_str,
                    "dex_chart": indodax_url,
                    "photon_link": indodax_url
                }
                signals.append(signal_entry)
        except Exception as e:
            print(f"Error checking {symbol}: {e}")
            
    return signals

def save_signals(signals_data):
    with open(SIGNALS_FILE, "w") as f:
        json.dump(signals_data, f, indent=2)

def main():
    new_signals = fetch_whale_signals()
    save_signals(new_signals)
    print(f"✅ Sinyal real-time berhasil diperbarui!")

if __name__ == "__main__":
    main()
