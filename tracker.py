import os
import json
import requests
from datetime import datetime

SIGNALS_FILE = "signals.json"

# Daftar koin Indodax yang ingin dipantau transaksi pausnya
INDODAX_COINS = [
    'PEPE', 'DOGE', 'BONK', 'FLOKI', 'WIF', 'POPCAT', 'MEME',
    'ACT', 'GRIFFAIN', 'GOAT', 'SUI', 'JUP', 'RAY', 'ONDO'
]

def fetch_whale_signals():
    signals = []
    
    for symbol in INDODAX_COINS:
        try:
            # Cari pair trading paling aktif untuk koin ini di DexScreener
            search_url = f"https://api.dexscreener.com/latest/dex/search?q={symbol}"
            res = requests.get(search_url, timeout=5).json()
            pairs = res.get('pairs', [])
            
            if not pairs:
                continue
                
            # Ambil pair terbaik
            pair = pairs[0]
            chain_id = pair.get('chainId', 'solana').upper()
            price_usd = float(pair.get('priceUsd', 0) or 0)
            vol_5m = float(pair.get('volume', {}).get('m5', 0) or 0)
            token_symbol = pair.get('baseToken', {}).get('symbol', '').upper()
            
            # Pastikan simbolnya cocok
            if token_symbol != symbol:
                continue
                
            price_idr = price_usd * 15800
            val_idr = vol_5m * 15800
            
            # Deteksi jika ada transaksi/volume berjalan (Minimal Rp 500rb dalam 5m)
            if val_idr >= 500_000 and price_idr > 0:
                pair_addr = pair.get('pairAddress', '')
                wallet_short = f"0x{pair_addr[:4]}...{pair_addr[-4:]}"
                tx_hash = f"tx_{symbol}_{int(datetime.utcnow().timestamp())}"
                indodax_url = f"https://indodax.com/market/{symbol}IDR"
                
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
                    "market_cap": f"Sinyal Pembelian On-Chain ({chain_id})",
                    "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
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
    print("Memeriksa aktivitas dompet paus di koin-koin pilihan Indodax...")
    new_signals = fetch_whale_signals()
    if new_signals:
        save_signals(new_signals)
        print(f"✅ BERHASIL! Ditemukan {len(new_signals)} sinyal aktif.")
    else:
        print("Tidak ada sinyal terdeteksi saat ini.")

if __name__ == "__main__":
    main()
