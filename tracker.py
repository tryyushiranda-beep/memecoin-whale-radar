import os
import json
import requests
from datetime import datetime

SIGNALS_FILE = "signals.json"

# Daftar token non-memecoin / koin utama & stablecoin yang disaring
EXCLUDED_COINS = {
    'BTC', 'USDT', 'USDC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOT', 
    'LTC', 'BCH', 'XLM', 'TRX', 'MATIC', 'AVAX', 'UNI', 'LINK', 'XMR',
    'ETC', 'FIL', 'APT', 'NEAR', 'ALGO', 'ICP', 'VET', 'HBAR', 'ICP'
}

def fetch_indodax_top_memecoins():
    """
    Mengambil data pasar langsung dari API Resmi Indodax (summaries)
    dan memfilter koin-koin paling aktif / volume terbesar khusus pasar Indodax.
    """
    signals = []
    
    try:
        url = "https://indodax.com/api/summaries"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        tickers = data.get('tickers', {})
        prices = data.get('prices', {})
        
        candidates = []
        
        for pair, details in tickers.items():
            # Hanya ambil pasangan berbasis IDR (contoh: doge_idr, pepe_idr)
            if pair.endswith('_idr'):
                coin_symbol = pair.replace('_idr', '').upper()
                
                # Filter: Abaikan koin utama & stablecoin
                if coin_symbol in EXCLUDED_COINS:
                    continue
                
                vol_idr = float(details.get('vol_idr', 0) or 0)
                last_price = float(details.get('last', 0) or 0)
                high_price = float(details.get('high', 0) or 0)
                low_price = float(details.get('low', 0) or 0)
                
                # Hitung estimasi persentase perubahan harga harian
                price_change_pct = 0
                if low_price > 0:
                    price_change_pct = ((last_price - low_price) / low_price) * 100
                
                # Masukkan koin yang memiliki aktivitas volume di Indodax (minimal Rp 50 Juta)
                if vol_idr >= 50_000_000:
                    candidates.append({
                        "symbol": coin_symbol,
                        "name": details.get('name', coin_symbol),
                        "last_price": last_price,
                        "vol_idr": vol_idr,
                        "change_pct": price_change_pct,
                        "pair": pair
                    })
        
        # Urutkan koin berdasarkan volume transaksi IDR terbesar di Indodax saat ini
        candidates.sort(key=lambda x: x['vol_idr'], reverse=True)
        
        # Format ke bentuk sinyal radar
        for item in candidates[:25]: # Ambil 25 koin teratas di Indodax
            tx_hash = f"idx_{item['symbol']}_{int(datetime.utcnow().timestamp())}"
            indodax_url = f"https://indodax.com/market/{item['symbol']}IDR"
            
            # Konversi format USD tiruan agar kompatibel dengan index.html yang ada
            val_usd = item['vol_idr'] / 15800
            
            signal_entry = {
                "id": tx_hash,
                "hash": tx_hash,
                "chain": "INDODAX",
                "action": "BUY",
                "wallet_name": "🔥 Indodax Top Volume",
                "token": item['symbol'],
                "token_name": f"Harga: Rp {item['last_price']:,.0f} | 24h Vol: Rp {item['vol_idr']:,.0f}",
                "amount": f"{item['vol_idr']/item['last_price']:,.0f}" if item['last_price'] > 0 else "1,000,000",
                "est_val_usd": f"${val_usd:,.2f}",
                "liquidity": f"${val_usd * 1.5:,.0f}",
                "market_cap": f"${val_usd * 10:,.0f}",
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
    print("Memantau koin & memecoin teraktif LANGSUNG DARI INDODAX...")
    new_signals = fetch_indodax_top_memecoins()
    
    if new_signals:
        save_signals(new_signals)
        print(f"✅ BERHASIL! {len(new_signals)} koin teraktif Indodax berhasil disimpan.")
    else:
        print("Gagal mengambil data dari Indodax.")

if __name__ == "__main__":
    main()
