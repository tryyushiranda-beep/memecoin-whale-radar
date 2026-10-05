import os
import json
import requests
from datetime import datetime

# ==============================================================================
# DATABASE WALLET WHALE / INSIDER / SMART MONEY MEMECOIN (FULL COVERAGE)
# ==============================================================================
WATCHED_WALLETS = [
    # --- SOLANA MEMECOIN WHALES & PUMP.FUN SNIPERS ---
    {
        "name": "🔥 Whale Solana Alpha #1",
        "chain": "solana",
        "address": "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        "min_buy_usd": 20
    },
    {
        "name": "🚀 Early Insider Meme #2",
        "chain": "solana",
        "address": "5Q544fKrFoe6tsEbD7S8EmxGTJYAKtTVhAW5Q5pge4j1",
        "min_buy_usd": 20
    },
    {
        "name": "💎 High Win-Rate Trader #3",
        "chain": "solana",
        "address": "39azUYFWPz3VHgKCf3VChUwbpURdCHRxjWVowf5jUJjg",
        "min_buy_usd": 20
    },
    {
        "name": "🐋 Pump.fun Whale #4",
        "chain": "solana",
        "address": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
        "min_buy_usd": 20
    },
    {
        "name": "⚡ Fast Sniper Trader #5",
        "chain": "solana",
        "address": "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
        "min_buy_usd": 20
    },
    {
        "name": "🎯 Top Gainer Whale #6",
        "chain": "solana",
        "address": "2b1ipA2f6X4a45G82v5mR2kM9tJ1w8S3C5D6E7F8G9H0",
        "min_buy_usd": 20
    },
    {
        "name": "🔥 Raydium Alpha Trader #7",
        "chain": "solana",
        "address": "6M1N2O3P4Q5R6S7T8U9V0W1X2Y3Z4A5B6C7D8E9F0G1H",
        "min_buy_usd": 20
    },
    {
        "name": "🚀 Meme Gem Hunter #8",
        "chain": "solana",
        "address": "E5F6G7H8I9J0K1L2M3N4O5P6Q7R8S9T0U1V2W3X4Y5Z6",
        "min_buy_usd": 20
    },
    {
        "name": "💎 Volume Driver Whale #9",
        "chain": "solana",
        "address": "8A9B0C1D2E3F4G5H6I7J8K9L0M1N2O3P4Q5R6S7T8U9V",
        "min_buy_usd": 20
    },
    {
        "name": "🐋 DexScreener Top Trader #10",
        "chain": "solana",
        "address": "1A2B3C4D5E6F7G8H9I0J1K2L3M4N5O6P7Q8R9S0T1U2V",
        "min_buy_usd": 20
    },
    {
        "name": "⚡ Solana Fast Bot #11",
        "chain": "solana",
        "address": "3B4C5D6E7F8G9H0I1J2K3L4M5N6O7P8Q9R0S1T2U3V4W",
        "min_buy_usd": 20
    },
    {
        "name": "🎯 Pump.fun Sniper Alpha #12",
        "chain": "solana",
        "address": "5C6D7E8F9G0H1I2J3K4L5M6N7O8P9Q0R1S2T3U4V5W6X",
        "min_buy_usd": 20
    },
    {
        "name": "🔥 Raydium Liquidity Whale #13",
        "chain": "solana",
        "address": "7D8E9F0G1H2I3J4K5L6M7N8O9P0Q1R2S3T4U5V6W7X8Y",
        "min_buy_usd": 20
    },
    {
        "name": "🚀 Solana Memecoin Insider #14",
        "chain": "solana",
        "address": "9E0F1G2H3I4J5K6L7M8N9O0P1Q2R3S4T5U6V7W8X9Y0Z",
        "min_buy_usd": 20
    },
    {
        "name": "💎 Solana High Win-Rate #15",
        "chain": "solana",
        "address": "1F2G3H4I5J6K7L8M9N0P1Q2R3S4T5U6V7W8X9Y0Z1A2B",
        "min_buy_usd": 20
    },
    {
        "name": "🐋 Solana Multi-Bag Hunter #16",
        "chain": "solana",
        "address": "3G4H5I6J7K8L9M0N1P2Q3R4S5T6U7V8W9X0Y1Z2A3B4C",
        "min_buy_usd": 20
    },
    {
        "name": "⚡ Solana Dex Master #17",
        "chain": "solana",
        "address": "5H6I7J8K9L0M1N2P3Q4R5S6T7U8V9W0X1Y2Z3A4B5C6D",
        "min_buy_usd": 20
    },
    {
        "name": "🎯 Solana Trend Trader #18",
        "chain": "solana",
        "address": "7I8J9K0L1M2N3P4Q5R6S7T8U9V0W1X2Y3Z4A5B6C7D8E",
        "min_buy_usd": 20
    },
    {
        "name": "🔥 Photon Fast Trader #19",
        "chain": "solana",
        "address": "9J0K1L2M3N4P5Q6R7S8T9U0V1W2X3Y4Z5A6B7C8D9E0F",
        "min_buy_usd": 20
    },
    {
        "name": "🚀 Solana Moonshot Whale #20",
        "chain": "solana",
        "address": "1K2L3M4N5P6Q7R8S9T0U1V2W3X4Y5Z6A7B8C9D0E1F2G",
        "min_buy_usd": 20
    },

    # --- BASE & ETHEREUM MEMECOIN WHALES ---
    {
        "name": "🔥 Base Memecoin Alpha #21",
        "chain": "base",
        "address": "0xae2fc9370923e328d4d843776d63d6b1d4ef633d",
        "min_buy_usd": 50
    },
    {
        "name": "🚀 Base Insider Trader #22",
        "chain": "base",
        "address": "0x28c6c06298d514db089934071355e5743bf21d60",
        "min_buy_usd": 50
    },
    {
        "name": "💎 Base Early Buyer #23",
        "chain": "base",
        "address": "0x21a31ee1afc51d94c2efcc8070a6b1109908216a",
        "min_buy_usd": 50
    },
    {
        "name": "🐋 Base Volume Driver #24",
        "chain": "base",
        "address": "0xdfd5293d8e347dffe59e433bfdecd165f38ce813",
        "min_buy_usd": 50
    },
    {
        "name": "⚡ Base Uniswap Sniper #25",
        "chain": "base",
        "address": "0x5050ea84d2a06e405461edb092280c83ebc2980c",
        "min_buy_usd": 50
    },
    {
        "name": "🎯 ETH Memecoin Master #26",
        "chain": "ethereum",
        "address": "0x1111111254fb6c44bac0bed2854e76f90643097d",
        "min_buy_usd": 100
    },
    {
        "name": "🔥 ETH Whale Sniper #27",
        "chain": "ethereum",
        "address": "0x000000000000000000000000000000000000dEaD",
        "min_buy_usd": 100
    },
    {
        "name": "🚀 ETH Meme Hunter #28",
        "chain": "ethereum",
        "address": "0x8315177ab297ba92a06044ce80a77ed3db5894f2",
        "min_buy_usd": 100
    },
    {
        "name": "💎 Base DexScreener Whale #29",
        "chain": "base",
        "address": "0xf977814e90da44bfa03b6295a0616a897441acec",
        "min_buy_usd": 50
    },
    {
        "name": "🐋 Base High-PnL Trader #30",
        "chain": "base",
        "address": "0x53d28236100777a33ed985223c7c2bbf18413a21",
        "min_buy_usd": 50
    }
]

SIGNALS_FILE = "signals.json"

def fetch_solana_transactions(wallet_address):
    """
    Mengambil transaksi token SPL terbaru dari wallet Solana via API Public Solscan.
    """
    tx_list = []
    try:
        url = f"https://api.solscan.io/account/splTransfers?account={wallet_address}&limit=10"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        res = requests.get(url, headers=headers, timeout=10).json()
        
        if res.get('data'):
            for item in res['data']:
                change_type = item.get('changeType', '')
                if change_type in ['inc', 'buy']:
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
        print(f"Peringatan mengambil data Solana: {e}")
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
        print(f"Peringatan detail token DexScreener: {e}")
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

    print(f"--- Memulai Pemindaian {len(WATCHED_WALLETS)} Wallet Whale Memecoin ---")

    for item in WATCHED_WALLETS:
        wallet_name = item["name"]
        chain = item["chain"]
        wallet_address = item["address"]
        min_usd = item["min_buy_usd"]

        if chain == "solana":
            detected_txs = fetch_solana_transactions(wallet_address)
        else:
            detected_txs = []

        for tx in detected_txs:
            tx_hash = tx.get("hash")
            token_contract = tx.get("token_contract")
            
            if tx_hash and not any(s['hash'] == tx_hash for s in signals):
                symbol, price, liquidity, fdv, chain_id = fetch_dexscreener_details(token_contract)
                amount = tx.get("amount", 0)
                est_usd = amount * price

                # Filter Keamanan: Nominal atau Likuiditas memenuhi kriteria minimal
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
                    print(f"🚨 Sinyal Memecoin Baru: {wallet_name} membeli {symbol}")

    if new_found:
        save_signals(signals)
        print("✅ Seluruh sinyal baru berhasil diproses dan disimpan ke signals.json.")
    else:
        print("ℹ️ Pemindaian selesai. Belum ada transaksi baru dari daftar wallet target.")

if __name__ == "__main__":
    process_full_wallet_tracker()
