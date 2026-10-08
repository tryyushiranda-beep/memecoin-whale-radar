import os
import json
import requests
from datetime import datetime

SIGNALS_FILE = "signals.json"

# Daftar token utama / stablecoin yang disaring
EXCLUDED_COINS = {
    'BTC', 'USDT', 'USDC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOT', 
    'LTC', 'BCH', 'XLM', 'TRX', 'MATIC', 'AVAX', 'UNI', 'LINK', 'XMR',
    'ETC', 'FIL', 'APT', 'NEAR', 'ALGO', 'ICP', 'VET', 'HBAR'
}

def fetch_indodax_top_memecoins():
    signals = []
    
    try:
        url = "https://indodax.com/api/summaries"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        tickers = data.get('tickers', {})
        candidates = []
        
        for pair, details in tickers.items():
            if pair.endswith('_idr'):
                coin_symbol = pair.replace('_idr', '').upper()
                
                if coin_symbol in EXCLUDED_COINS:
                    continue
                
                vol_idr = float(details.get('vol_idr', 0) or 0)
                last_price = float(details.get('last', 0) or 0)
                high_price = float(details.get('high', 0) or 0)
                low_price = float(details.get('low', 0) or 0)
                
                # Hitung estimasi perubahan harga harian
                price_change_pct = 0
                if low_price > 0:
                    price_change_pct = ((last_price - low_price) / low_price) * 100
                
                if vol_idr >= 50_000_000:
                    candidates.append({
                        "symbol": coin_symbol,
                        "last_price": last_price,
                        "vol_idr": vol_idr,
                        "change_pct": price_change_pct,
                        "high": high_price,
                        "low": low_price
                    })
        
        # Urutkan koin berdasarkan volume IDR terbesar
        candidates.sort(key=lambda x: x['vol_idr'], reverse=True)
        
        for item in candidates[:25]:
            tx_hash = f"idx_{item['symbol']}_{int(datetime.utcnow().timestamp())}"
            indodax_url = f"https://indodax.com/market/{item['symbol']}IDR"
            
            val_usd = item['vol_idr'] / 15800
            
            signal_entry = {
                "id": tx_hash,
                "hash": tx_hash,
                "chain": "INDODAX",
                "action": "BUY",
                "wallet_name": "🔥 Indodax Active Volume",
                "token": item['symbol'],
                "token_name": f"Harga: Rp {item['last_price']:,.0f}",
                "amount": f"{item['vol_idr']/item['last_price']:,.0f}" if item['last_price'] > 0 else "0",
                "est_val_usd": f"${val_usd:,.2f}",
                "liquidity": f"Rp {item['vol_idr']:,.0f}",
                "market_cap": f"+{item['change_pct']:.2f}% (24h Range)",
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC"),
                "dex_chart": indodax_url,
                "photon_link": indodax_url
            }
            signals.append(signal_entry)
            
    except Exception as e:
        print(f"Error fetching Indodax summaries API: {e}")

    return signals

def save_signals(signals_data):
    with open(SIGNALS_FILE, "w") as f:
        json.dump(signals_data, f, indent=2)

def main():
    new_signals = fetch_indodax_top_memecoins()
    if new_signals:
        save_signals(new_signals)
        print(f"✅ BERHASIL! {len(new_signals)} koin Indodax disimpan.")

if __name__ == "__main__":
    main()
