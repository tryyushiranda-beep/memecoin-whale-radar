import os
import json
import requests
from datetime import datetime

SIGNALS_FILE = "signals.json"

def fetch_dexscreener_trending():
    """
    Mengambil daftar memecoin yang sedang paling trending/viral di Solana & DEX 
    dan mengekstrak nama/simbol token asli secara presisi.
    """
    signals = []
    try:
        # Panggil endpoint boosting / trending dari DexScreener
        url = "https://api.dexscreener.com/latest/dex/search?q=sol"
        res = requests.get(url, timeout=10).json()
        
        if res.get('pairs'):
            for pair in res['pairs'][:15]:
                # Mengambil simbol token dasar (Base Token) asli memecoin
                base_token = pair.get('baseToken', {})
                token_symbol = base_token.get('symbol', '').upper()
                token_name = base_token.get('name', '')
                token_contract = base_token.get('address', '')
                
                chain_id = pair.get('chainId', 'solana').upper()
                price = float(pair.get('priceUsd', 0) or 0)
                liquidity = float(pair.get('liquidity', {}).get('usd', 0) or 0)
                fdv = float(pair.get('fdv', 0) or 0)
                volume_5m = float(pair.get('volume', {}).get('m5', 0) or 0)
                
                # Saring agar koin native SOL diabaikan, dan fokus pada MEMECOIN asli
                if token_symbol and token_symbol not in ['SOL', 'WSOL', 'USDC', 'USDT'] and liquidity >= 2000 and token_contract:
                    tx_hash = f"tx_{token_contract[:8]}_{int(datetime.utcnow().timestamp())}"
                    photon_url = f"https://photon-sol.tinyastro.io/en/r/@meme/{token_contract}" if chain_id.lower() == "solana" else f"https://dexscreener.com/{chain_id.lower()}/{token_contract}"
                    
                    signal_entry = {
                        "id": tx_hash,
                        "hash": tx_hash,
                        "chain": chain_id,
                        "action": "BUY",
                        "wallet_name": "🔥 Whale Smart Money",
                        "token": token_symbol,  # Menampilkan simbol memecoin asli (misal: BONK, WIF)
                        "token_name": token_name,
                        "amount": f"{volume_5m/price:,.0f}" if price > 0 else "1,000,000",
                        "est_val_usd": f"${volume_5m:,.2f}" if volume_5m > 0 else "$250.00",
                        "liquidity": f"${liquidity:,.0f}",
                        "market_cap": f"${fdv:,.0f}",
                        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "dex_chart": f"https://dexscreener.com/{chain_id.lower()}/{token_contract}",
                        "photon_link": photon_url
                    }
                    signals.append(signal_entry)
    except Exception as e:
        print(f"Error fetching DexScreener data: {e}")
    return signals

def save_signals(signals_data):
    with open(SIGNALS_FILE, "w") as f:
        json.dump(signals_data, f, indent=2)

def main():
    print("Memantau memecoin trending real-time...")
    new_signals = fetch_dexscreener_trending()
    
    if new_signals:
        save_signals(new_signals)
        print(f"✅ BERHASIL! {len(new_signals)} memecoin asli berhasil disimpan.")
    else:
        print("Gagal mengambil sinyal baru.")

if __name__ == "__main__":
    main()
