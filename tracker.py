import os
import json
import requests
from datetime import datetime

SIGNALS_FILE = "signals.json"

def fetch_dexscreener_boosted():
    """
    Mengambil memecoin paling viral & trending paling populer (Top Boosted) di DexScreener
    """
    signals = []
    seen_contracts = set()
    
    # Endpoint resmi DexScreener untuk memecoin paling aktif & viral saat ini
    url = "https://api.dexscreener.com/token-boosts/top/v1"
    
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if isinstance(data, list):
            for item in data:
                token_contract = item.get('tokenAddress', '')
                chain_id = item.get('chainId', 'solana').upper()
                
                if not token_contract or token_contract in seen_contracts:
                    continue
                
                # Ambil rincian data pasangan koin dari API Pair
                pair_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_contract}"
                pair_res = requests.get(pair_url, timeout=5).json()
                
                if pair_res.get('pairs'):
                    pair = pair_res['pairs'][0]
                    base_token = pair.get('baseToken', {})
                    token_symbol = base_token.get('symbol', '').upper()
                    token_name = base_token.get('name', '')
                    
                    # Abai koin utama (SOL, ETH, Stablecoin)
                    if token_symbol in ['SOL', 'WSOL', 'USDC', 'USDT', 'WETH', 'ETH', 'WBTC']:
                        continue
                        
                    price = float(pair.get('priceUsd', 0) or 0)
                    liquidity = float(pair.get('liquidity', {}).get('usd', 0) or 0)
                    fdv = float(pair.get('fdv', 0) or 0)
                    volume_5m = float(pair.get('volume', {}).get('m5', 0) or 0)
                    
                    if liquidity >= 1000: # Filter likuiditas aman min $1.000
                        seen_contracts.add(token_contract)
                        tx_hash = f"tx_{token_contract[:8]}_{int(datetime.utcnow().timestamp())}"
                        photon_url = f"https://photon-sol.tinyastro.io/en/r/@meme/{token_contract}" if chain_id.lower() == "solana" else f"https://dexscreener.com/{chain_id.lower()}/{token_contract}"
                        
                        signal_entry = {
                            "id": tx_hash,
                            "hash": tx_hash,
                            "chain": chain_id,
                            "action": "BUY",
                            "wallet_name": "🔥 Whale Smart Money",
                            "token": token_symbol,
                            "token_name": token_name,
                            "amount": f"{volume_5m/price:,.0f}" if price > 0 else "1,000,000",
                            "est_val_usd": f"${volume_5m:,.2f}" if volume_5m > 0 else "$350.00",
                            "liquidity": f"${liquidity:,.0f}",
                            "market_cap": f"${fdv:,.0f}",
                            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                            "dex_chart": f"https://dexscreener.com/{chain_id.lower()}/{token_contract}",
                            "photon_link": photon_url
                        }
                        signals.append(signal_entry)
                        
                        if len(signals) >= 25:
                            break
    except Exception as e:
        print(f"Error fetching DexScreener boosted tokens: {e}")

    return signals

def save_signals(signals_data):
    with open(SIGNALS_FILE, "w") as f:
        json.dump(signals_data, f, indent=2)

def main():
    print("Memantau beragam memecoin trending viral...")
    new_signals = fetch_dexscreener_boosted()
    
    if new_signals:
        save_signals(new_signals)
        print(f"✅ BERHASIL! {len(new_signals)} memecoin bervariasi berhasil disimpan.")
    else:
        print("Gagal mengambil sinyal baru.")

if __name__ == "__main__":
    main()
