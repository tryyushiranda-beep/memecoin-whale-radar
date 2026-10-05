import os
import json
import requests
from datetime import datetime

# 1. DATABASE WALLET MEMECOIN YANG DIPANTAU (Solana / EVM)
WATCHED_WALLETS = [
    {
        "name": "Memecoin Whale Alpha",
        "chain": "solana",
        "address": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU", # Ganti dengan wallet target Anda
        "min_buy_usd": 100
    }
]

SIGNALS_FILE = "signals.json"

def fetch_solana_wallet_txs(wallet_address):
    """
    Mengambil transaksi token terbaru dari wallet Solana secara otomatis & gratis via API Solscan/Public.
    """
    tx_list = []
    try:
        url = f"https://api.solscan.io/account/splTransfers?account={wallet_address}&limit=5"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10).json()
        
        if res.get('data'):
            for item in res['data']:
                # Mengambil transaksi token yang masuk/dibeli
                if item.get('changeType') == 'inc':  # 'inc' = Incoming/Buy
                    tx_list.append({
                        "hash": item.get('signature'),
                        "token_contract": item.get('tokenAddress'),
                        "symbol": item.get('symbol', 'MEME'),
                        "amount": float(item.get('changeAmount', 0)) / (10 ** int(item.get('decimals', 9)))
                    })
    except Exception as e:
        print(f"Peringatan saat mengambil transaksi Solana: {e}")
    return tx_list

def fetch_dexscreener_details(token_address):
    """
    Mengambil harga, likuiditas, dan Market Cap token secara otomatis dari DexScreener API.
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

        # AMBIL TRANSAKSI SECARA OTOMATIS
        if chain == "solana":
            detected_txs = fetch_solana_wallet_txs(wallet_address)
        else:
            detected_txs = []

        for tx in detected_txs:
            tx_hash = tx.get("hash")
            token_contract = tx.get("token_contract")
            
            # Cek apakah transaksi ini belum pernah dicatat
            if not any(s['hash'] == tx_hash for s in signals):
                symbol, price, liquidity, fdv, chain_id = fetch_dexscreener_details(token_contract)
                amount = tx.get("amount", 0)
                est_usd = amount * price

                # Filter Keamanan: Minimal transaksi $100 & Likuiditas minimal $2,000
                if est_usd >= min_usd or liquidity >= 2000:
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
        print("Sinyal Memecoin otomatis baru berhasil ditemukan dan disimpan!")
    else:
        print("Pemeriksaan selesai. Belum ada transaksi baru.")

if __name__ == "__main__":
    process_memecoin_tracker()
