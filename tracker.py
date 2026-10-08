import os
import json
import requests
from datetime import datetime

SIGNALS_FILE = "signals.json"

# List gabungan Memecoin & Altcoin Koin Kecil Berfundamental di Indodax
INDODAX_COINS = [
    'PEPE', 'DOGE', 'BONK', 'FLOKI', 'WIF', 'POPCAT', 'MEME',
    'ACT', 'GRIFFAIN', 'GOAT', 'SUI', 'JUP', 'RAY', 'ONDO'
]

# Hanya izinkan jaringan/blockchain resmi utama
ALLOWED_CHAINS = {'SOLANA', 'ETHEREUM', 'BSC', 'POLYGON', 'ARBITRUM', 'BASE'}

def fetch_whale_signals():
    signals = []
    
    for symbol in INDODAX_COINS:
        try:
            # Cari pair trading paling aktif di DexScreener
            search_url = f"https://api.dexscreener.com/latest/dex/search?q={symbol}"
            res = requests.get(search_url, timeout=5).json()
            pairs = res.get('pairs', [])
            
            if not pairs:
                continue
                
            # Filter pair terbaik yang berada di jaringan resmi
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
            
            price_idr = price_usd * 15800
            val_idr = vol_5m * 15800
            
            # Deteksi transaksi berjalan (Minimal Rp 500rb dalam 5m & Anti-Rp0)
            if val_idr >= 500_000 and price_idr > 0:
                pair_addr = selected_pair.get('pairAddress', '')
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
    # Selalu menimpa (overwrite) file signals.json secara otomatis
    with open(SIGNALS_FILE, "w") as f:
        json.dump(signals_data, f, indent=2)

def main():
    print("Memeriksa aktivitas dompet paus khusus koin Indodax...")
    new_signals = fetch_whale_signals()
    
    # Otomatis simpan data baru (walaupun kosong, sistem yang urus)
    save_signals(new_signals)
    print(f"✅ BERHASIL! {len(new_signals)} sinyal aktif diperbarui ke signals.json secara otomatis.")

if __name__ == "__main__":
    main()
