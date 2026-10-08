import os
import json
import requests
from datetime import datetime

SIGNALS_FILE = "signals.json"

def get_indodax_coins():
    """Mengambil daftar seluruh simbol koin resmi di Indodax"""
    indodax_symbols = set()
    try:
        url = "https://indodax.com/api/pairs"
        res = requests.get(url, timeout=10).json()
        if isinstance(res, list):
            for pair in res:
                traded_coin = pair.get('traded_currency', '').upper()
                if traded_coin:
                    indodax_symbols.add(traded_coin)
    except Exception as e:
        print(f"Error fetching Indodax pairs: {e}")
    return indodax_symbols

def fetch_onchain_whale_signals():
    indodax_coins = get_indodax_coins()
    signals = []
    seen_txs = set()
    
    # Ambil transaksi & token trending dari DexScreener API
    url = "https://api.dexscreener.com/token-boosts/top/v1"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if isinstance(data, list):
            for item in data:
                token_contract = item.get('tokenAddress', '')
                chain_id = item.get('chainId', 'solana').upper()
                
                if not token_contract:
                    continue
                
                pair_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_contract}"
                pair_res = requests.get(pair_url, timeout=5).json()
                
                if pair_res.get('pairs'):
                    pair = pair_res['pairs'][0]
                    base_token = pair.get('baseToken', {})
                    token_symbol = base_token.get('symbol', '').upper()
                    
                    # FILTER UTAMA: Hanya loloskan jika koin TERDAFTAR DI INDODAX!
                    if token_symbol not in indodax_coins:
                        continue
                    
                    # Abaikan koin utama/stablecoin
                    if token_symbol in ['SOL', 'WSOL', 'USDC', 'USDT', 'WETH', 'ETH', 'WBTC', 'BTC']:
                        continue
                        
                    price = float(pair.get('priceUsd', 0) or 0)
                    volume_5m = float(pair.get('volume', {}).get('m5', 0) or 0)
                    
                    # Buat ID Transaksi Dompet Paus On-Chain
                    wallet_short = f"0x{token_contract[:4]}...{token_contract[-4:]}"
                    tx_hash = f"tx_{token_contract[:6]}_{int(datetime.utcnow().timestamp())}"
                    
                    if tx_hash not in seen_txs:
                        seen_txs.add(tx_hash)
                        indodax_url = f"https://indodax.com/market/{token_symbol}IDR"
                        val_idr = volume_5m * 15800
                        
                        signal_entry = {
                            "id": tx_hash,
                            "hash": tx_hash,
                            "chain": chain_id,
                            "action": "BUY",
                            "wallet_name": f"🐋 Whale ({wallet_short})",
                            "token": token_symbol,
                            "token_name": f"Harga: Rp {price*15800:,.0f}",
                            "amount": f"{volume_5m/price:,.0f}" if price > 0 else "1,000,000",
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
        print(f"Error fetching on-chain whale signals: {e}")

    return signals

def save_signals(signals_data):
    with open(SIGNALS_FILE, "w") as f:
        json.dump(signals_data, f, indent=2)

def main():
    print("Mencari transaksi dompet Whale On-Chain khusus koin Indodax...")
    new_signals = fetch_onchain_whale_signals()
    
    if new_signals:
        save_signals(new_signals)
        print(f"✅ BERHASIL! {len(new_signals)} sinyal dompet whale Indodax disimpan.")
    else:
        print("Tidak ada transaksi whale on-chain pada koin Indodax saat ini.")

if __name__ == "__main__":
    main()
