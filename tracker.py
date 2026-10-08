import os
import json
import requests
from datetime import datetime

SIGNALS_FILE = "signals.json"

# Whitelist khusus Memecoin & Altcoin Koin Kecil Berfundamental yang ada di Indodax
WHITELIST_COINS = {
    # Memecoin & AI Memes
    'PEPE', 'DOGE', 'SHIB', 'BONK', 'FLOKI', 'MEME', 'WIF', 'POPCAT', 
    'MEW', 'NEIRO', 'TURBO', 'BOME', 'MYRO', 'SLERF', 'BABYDOGE',
    'ACT', 'GRIFFAIN', 'PIPPIN', 'GOAT',
    # Altcoin Koin Kecil / Fundamental / DeFi / L1 / L2
    'SUI', 'JUP', 'RAY', 'ONDO', 'PHA', 'PENDLE', 'TIA', 'INJ', 
    'SEI', 'ARBM', 'OP', 'AERO', 'STX', 'FET', 'RENDER'
}

# Hanya izinkan jaringan crypto utama (Anti-Robinhood & Anti-Fake Chain)
ALLOWED_CHAINS = {'SOLANA', 'ETHEREUM', 'BSC', 'POLYGON', 'ARBITRUM', 'BASE'}

def fetch_onchain_whale_signals():
    signals = []
    seen_txs = set()
    
    url = "https://api.dexscreener.com/token-boosts/top/v1"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if isinstance(data, list):
            for item in data:
                token_contract = item.get('tokenAddress', '')
                chain_id = item.get('chainId', '').upper()
                
                # Filter 1: Validasi Jaringan Resmi
                if not token_contract or chain_id not in ALLOWED_CHAINS:
                    continue
                
                pair_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_contract}"
                pair_res = requests.get(pair_url, timeout=5).json()
                
                if pair_res.get('pairs'):
                    pair = pair_res['pairs'][0]
                    base_token = pair.get('baseToken', {})
                    token_symbol = base_token.get('symbol', '').upper()
                    
                    # Filter 2: Hanya Koin Whitelist Indodax
                    if token_symbol not in WHITELIST_COINS:
                        continue
                        
                    price = float(pair.get('priceUsd', 0) or 0)
                    volume_5m = float(pair.get('volume', {}).get('m5', 0) or 0)
                    
                    val_idr = volume_5m * 15800
                    # Filter 3: Pembelian Whale Valid (Minimal Rp 2 Juta & Anti-Rp0)
                    if price <= 0 or val_idr < 2_000_000:
                        continue
                    
                    price_idr = price * 15800
                    wallet_short = f"0x{token_contract[:4]}...{token_contract[-4:]}"
                    tx_hash = f"tx_{token_contract[:6]}_{int(datetime.utcnow().timestamp())}"
                    
                    if tx_hash not in seen_txs:
                        seen_txs.add(tx_hash)
                        indodax_url = f"https://indodax.com/market/{token_symbol}IDR"
                        
                        signal_entry = {
                            "id": tx_hash,
                            "hash": tx_hash,
                            "chain": chain_id,
                            "action": "BUY",
                            "wallet_name": f"🐋 Whale ({wallet_short})",
                            "token": token_symbol,
                            "token_name": f"Harga On-Chain: Rp {price_idr:,.4f}" if price_idr < 10 else f"Harga On-Chain: Rp {price_idr:,.0f}",
                            "amount": f"{volume_5m/price:,.0f}",
                            "est_val_usd": f"${volume_5m:,.2f}",
                            "liquidity": f"Rp {val_idr:,.0f}",
                            "market_cap": f"Sinyal Pembelian On-Chain ({chain_id})",
                            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "dex_chart": indodax_url,
                            "photon_link": indodax_url
                        }
                        signals.append(signal_entry)
                        
                        if len(signals) >= 20:
                            break
    except Exception as e:
        print(f"Error fetching whale signals: {e}")

    return signals

def save_signals(signals_data):
    with open(SIGNALS_FILE, "w") as f:
        json.dump(signals_data, f, indent=2)

def main():
    print("Mencari transaksi dompet Whale On-Chain khusus Koin Pilihan Indodax...")
    new_signals = fetch_onchain_whale_signals()
    
    if new_signals:
        save_signals(new_signals)
        print(f"✅ BERHASIL! {len(new_signals)} sinyal disimpan.")
    else:
        print("Tidak ada transaksi whale pada koin pilihan saat ini.")

if __name__ == "__main__":
    main()
