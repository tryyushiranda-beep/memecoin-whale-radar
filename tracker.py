import os
import json
import requests
from datetime import datetime

# 1. DATABASE WALLET WHALE / INSIDER MEMECOIN TARGET
# Masukkan alamat wallet whale memecoin (Solana / Ethereum / Base)
WATCHED_WALLETS = [
    {
        "name": "Memecoin Whale Alpha (SOL)",
        "chain": "solana",
        "address": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        "min_buy_usd": 200
    },
    {
        "name": "Inside Trader Memecoin (ETH/BASE)",
        "chain": "base",
        "address": "0xae2fc9370923e328d4d843776d63d6b1d4ef633d",
        "min_buy_usd": 500
    }
]

SIGNALS_FILE = "signals.json"

def fetch_dexscreener_details(token_address):
    """
    Mengambil data real-time memecoin dari DexScreener (Mendukung Solana, Base, Ethereum, BNB).
    """
    try:
        url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
        res = requests.get(url, timeout=5).json()
        if res.get('pairs'):
            pair = res['pairs'][0]
            price = float(pair.get('priceUsd', 0))
            liquidity = float(pair.get('liquidity', {}).get('usd', 0))
            fdv = float(pair.get('fdv', 0))
            symbol = pair.get('baseToken', {}).get('symbol', 'UNKNOWN')
            chain_id = pair.get('chainId', 'solana')
            return symbol, price, liquidity, fdv, chain_id
    except Exception as e:
        print(f"Error checking memecoin: {e}")
    return "UNKNOWN", 0, 0, 0, "solana"

def load_existing_signals():
    if os.path.exists(SIGNALS_FILE):
        try:
            with open(SIGNALS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_signals(signals_data):
    with open(SIGNALS_FILE, "w") as f:
        json.dump(signals_data[:50], f, indent=2)

def process_memecoin_tracker():
    signals = load_existing_signals()
    new_found = False

    for item in WATCHED_WALLETS:
        wallet_name = item["name"]
        chain = item["chain"]
        wallet_address = item["address"]
        min_usd = item["min_buy_usd"]

        # Memantau transaksi wallet target
        # Mengintegrasikan token kontrak memecoin yang baru saja dibeli
        detected_txs = [] 

        for tx in detected_txs:
            tx_hash = tx.get("hash")
            token_contract = tx.get("token_contract")
            
            if not any(s['hash'] == tx_hash for s in signals):
                symbol, price, liquidity, fdv, chain_id = fetch_dexscreener_details(token_contract)
                amount = tx.get("amount", 0)
                est_usd = amount * price

                # FILTER MEMECOIN AMAN:
                # 1. Nilai transaksi memenuhi kriteria minimal
                # 2. Likuiditas minimal $5,000 agar aman dari koin rugpull instan
                if est_usd >= min_usd and liquidity >= 5000:
                    photon_url = f"https://photon-sol.tinyastro.io/en/r/@meme/{token_contract}" if chain_id == "solana" else f"https://dexscreener.com/{chain_id}/{token_contract}"
                    
                    signal_entry = {
                        "id": tx_hash,
                        "hash": tx_hash,
                        "chain": chain_id.upper(),
                        "action": "BUY",
                        "wallet_name": wallet_name,
                        "token": symbol,
                        "amount": f"{amount:,.2f}",
                        "est_val_usd": f"${est_usd:,.2f}" if est_usd > 0 else "N/A",
                        "liquidity": f"${liquidity:,.0f}",
                        "market_cap": f"${fdv:,.0f}",
                        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "dex_chart": f"https://dexscreener.com/{chain_id}/{token_contract}",
                        "photon_link": photon_url
                    }
                    signals.insert(0, signal_entry)
                    new_found = True

    if new_found:
        save_signals(signals)
        print("Sinyal Memecoin baru berhasil diproses dan disimpan!")

if __name__ == "__main__":
    process_memecoin_tracker()
