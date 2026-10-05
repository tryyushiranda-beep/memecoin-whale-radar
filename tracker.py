import os
import json
import requests
from datetime import datetime

# 1. DAFTAR WALLET WHALE / SMART MONEY TARGET (Solana / Base / EVM)
# Masukkan alamat wallet target yang ingin Anda pantau penuh 24/7
WATCHED_WALLETS = [
    {
        "name": "Smart Money Whale #1",
        "chain": "solana",
        "address": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU", # Alamat wallet target
        "min_buy_usd": 50
    },
    {
        "name": "Inside Memecoin Trader #2",
        "chain": "solana",
        "address": "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1",
        "min_buy_usd": 50
    }
]

SIGNALS_FILE = "signals.json"

def fetch_solana_transactions(wallet_address):
    """
    Mengambil transaksi token SPL terbaru dari wallet Solana secara real-time via API Public Solscan.
    """
    tx_list = []
    try:
        url = f"https://api.solscan.io/account/splTransfers?account={wallet_address}&limit=10"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=10).json()
        
        if res.get('data'):
            for item in res['data']:
                # Filter hanya transaksi masuk (BUY / Incoming Transfer)
                change_type = item.get('changeType', '')
                if change_type == 'inc' or change_type == 'buy':
                    decimals = int(item.get('decimals', 9) or 9)
                    raw_amount = float(item.get('changeAmount', 0))
                    amount = raw_amount / (10 ** decimals)
                    
                    tx_list.append({
                        "hash": item.get('signature'),
                        "token_contract": item.get('tokenAddress'),
                        "symbol": item.get('symbol', 'MEME'),
                        "amount": amount
                    })
    except Exception as e:
        print(f"Peringatan mengambil data transaksi Solana: {e}")
    return tx_list

def fetch_dexscreener_details(token_address):
    """
    Mengambil informasi lengkap memecoin (Harga, Likuiditas, Market Cap) via DexScreener API.
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
        print(f"Peringatan mengambil detail token DexScreener: {e}")
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

def process_full_wallet_tracker():
    signals = load_existing_signals()
    new_found = False

    print("--- Memulai Pemindaian Wallet Whale Memecoin ---")

    for item in WATCHED_WALLETS:
        wallet_name = item["name"]
        chain = item["chain"]
        wallet_address = item["address"]
        min_usd = item["min_buy_usd"]

        # Ambil transaksi terbaru secara otomatis
        if chain == "solana":
            detected_txs = fetch_solana_transactions(wallet_address)
        else:
            detected_txs = []

        for tx in detected_txs:
            tx_hash = tx.get("hash")
            token_contract = tx.get("token_contract")
            
            # Cek agar transaksi yang sudah dicatat tidak terduplikasi
            if tx_hash and not any(s['hash'] == tx_hash for s in signals):
                symbol, price, liquidity, fdv, chain_id = fetch_dexscreener_details(token_contract)
                amount = tx.get("amount", 0)
                est_usd = amount * price

                # Filter Keamanan:
                # 1. Nominal transaksi memenuhi batas minimal
                # 2. Likuiditas minimal $1,000 agar memecoin tidak rugpull seketika
                if est_usd >= min_usd or liquidity >= 1000:
                    photon_url = f"https://photon-sol.tinyastro.io/en/r/@meme/{token_contract}" if chain_id == "solana" else f"https://dexscreener.com/{chain_id}/{token_contract}"
                    
                    signal_entry = {
                        "id": tx_hash,
                        "hash": tx_hash,
                        "chain": chain_id.upper(),
                        "action": "BUY",
                        "wallet_name": wallet_name,
                        "token": symbol if symbol != 'UNKNOWN' else tx.get('symbol', 'MEME'),
                        "amount": f"{amount:,.2f}",
                        "est_val_usd": f"${est_usd:,.2f}" if est_usd > 0 else "N/A",
                        "liquidity": f"${liquidity:,.0f}" if liquidity > 0 else "N/A",
                        "market_cap": f"${fdv:,.0f}" if fdv > 0 else "N/A",
                        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "dex_chart": f"https://dexscreener.com/{chain_id}/{token_contract}",
                        "photon_link": photon_url
                    }
                    
                    signals.insert(0, signal_entry)
                    new_found = True
                    print(f"🚨 Sinyal Baru Terdeteksi: {wallet_name} membeli {symbol}")

    if new_found:
        save_signals(signals)
        print("✅ Seluruh sinyal baru berhasil diproses dan disimpan ke signals.json.")
    else:
        print("ℹ️ Pemindaian selesai. Belum ada transaksi baru dari wallet target.")

if __name__ == "__main__":
    process_full_wallet_tracker()
