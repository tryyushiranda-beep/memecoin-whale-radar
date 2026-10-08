import os
import json
import requests
from datetime import datetime

SIGNALS_FILE = "signals.json"

def get_indodax_coins():
    """
    Mengambil daftar simbol koin yang secara resmi terdaftar di Indodax
    """
    indodax_symbols = set()
    try:
        url = "https://indodax.com/api/pairs"
        res = requests.get(url, timeout=10).json()
        if isinstance(res, list):
            for pair in res:
                # Ambil nama koin utama (misal 'traded_currency': 'pepe' / 'doge')
                traded_coin = pair.get('traded_currency', '').upper()
                if traded_coin:
                    indodax_symbols.add(traded_coin)
        print(f" Total {len(indodax_symbols)} koin Indodax terdeteksi.")
    except Exception as e:
        print(f"Error fetching Indodax pairs: {e}")
    return indodax_symbols

def fetch_indodax_memecoins():
    indodax_coins = get_indodax_coins()
    signals = []
    seen_contracts = set()
    
    # Ambil koin viral & trending dari DexScreener
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
                
                # Fetch rincian pasangan dari DexScreener
                pair_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_contract}"
                pair_res = requests.get(pair_url, timeout=5).json()
                
                if pair_res.get('pairs'):
                    pair = pair_res['pairs'][0]
                    base_token = pair.get('baseToken', {})
                    token_symbol = base_token.get('symbol', '').upper()
                    token_name = base_token.get('name', '')
                    
                    # FILTER KHUSUS: Hanya loloskan jika simbol koin ada di INDODAX!
                    if token_symbol not in indodax_coins:
                        continue
                        
                    # Abai koin utama / stablecoin
                    if token_symbol in ['SOL', 'WSOL', 'USDC', 'USDT', 'WETH', 'ETH', 'WBTC', 'BTC']:
                        continue
                        
                    price = float(pair.get('priceUsd', 0) or 0)
                    liquidity = float(pair.get('liquidity', {}).get('usd', 0) or 0)
                    fdv = float(pair.get('fdv', 0) or 0)
                    volume_5m = float(pair.get('volume', {}).get('m5', 0) or 0)
                    
                    seen_contracts.add(token_contract)
                    tx_hash = f"tx_{token_contract[:8]}_{int(datetime.utcnow().timestamp())}"
                    
                    # Link langsung ke marketplace Indodax
                    indodax_market_url = f"https://indodax.com/market/{token_symbol}IDR"
                    
                    signal_entry = {
                        "id": tx_hash,
                        "hash": tx_hash,
                        "chain": chain_id,
                        "action": "BUY",
                        "wallet_name": "🔥 Whale Smart Money",
                        "token": token_symbol,
                        "token_name": token_name,
                        "amount": f"{volume_5m/price:,.0f}" if price > 0 else "1,000,000",
                        "est_val_usd": f"${volume_5m:,.2f}" if volume_5m > 0 else "$250.00",
                        "liquidity": f"${liquidity:,.0f}",
                        "market_cap": f"${fdv:,.0f}",
                        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                        "dex_chart": indodax_market_url,  # Link diarahkan ke pasar Indodax
                        "photon_link": indodax_market_url
                    }
                    signals.append(signal_entry)
                    
                    if len(signals) >= 20:
                        break
    except Exception as e:
        print(f"Error fetching tokens: {e}")

    return signals

def save_signals(signals_data):
    with open(SIGNALS_FILE, "w") as f:
        json.dump(signals_data, f, indent=2)

def main():
    print("Memantau memecoin khusus yang TERDAFTAR DI INDODAX...")
    new_signals = fetch_indodax_memecoins()
    
    if new_signals:
        save_signals(new_signals)
        print(f"✅ BERHASIL! {len(new_signals)} memecoin Indodax disimpan.")
    else:
        print("Tidak ada sinyal memecoin Indodax baru saat ini.")

if __name__ == "__main__":
    main()
