import requests
import time
import json

# ==========================================
# PARAMETER TERKUNCI (SESUAI STRATEGI)
# ==========================================
MIN_BUY_WALL_IDR = 150_000_000       # Minimal Tembok Beli Rp 150 Juta
MIN_HAKA_5M_IDR = 30_000_000         # Minimal HAKA Rp 30 Juta dalam 5 menit
MIN_VOL_24H_IDR = 50_000_000        # Minimal Volume 24 Jam Rp 50 Juta (Filter Koin Mati)
MAX_VOL_24H_IDR = 5_000_000_000      # Maksimal Volume 24 Jam Rp 5 Miliar (Filter Koin Berat)

INDODAX_SUMMARIES_URL = "https://indodax.com/api/summaries"
INDODAX_DEPTH_URL = "https://indodax.com/api/depth/"
INDODAX_TRADES_URL = "https://indodax.com/api/trades/"

# Memori lokal untuk fitur Anti-Spoofing
buy_wall_tracker = {}

def clean_expired_spoof_tracker():
    """Membersihkan memori Anti-Spoofing dari koin usang (mencegah memory leak)."""
    global buy_wall_tracker
    now = time.time()
    expired_keys = [k for k, v in buy_wall_tracker.items() if now - v.get('last_seen', 0) > 300]
    for k in expired_keys:
        del buy_wall_tracker[k]

def get_filtered_pairs():
    """Mengambil dan menyaring koin IDR berbobot ringan."""
    try:
        response = requests.get(INDODAX_SUMMARIES_URL, timeout=10).json()
        tickers = response.get('tickers', {})
        
        valid_pairs = []
        for pair_id, data in tickers.items():
            if pair_id.endswith('_idr'):
                try:
                    last_price = float(data.get('last', 0))
                    vol_idr = float(data.get('vol_idr', 0))
                except (ValueError, TypeError):
                    continue
                
                # Filter koin aktif dengan perputaran likuiditas kelas menengah-kecil
                if MIN_VOL_24H_IDR <= vol_idr <= MAX_VOL_24H_IDR and last_price > 0:
                    valid_pairs.append({
                        'id': pair_id,
                        'symbol': pair_id.replace('_idr', '').upper(),
                        'price': last_price
                    })
        return valid_pairs
    except Exception as e:
        print(f"[ERROR] Gagal mengambil data bursa: {e}")
        return []

def analyze_order_book(pair_id, current_price):
    """Menganalisis Tembok Beli (Buy Wall) & Ketebalan Antrean Jual (+30%)."""
    url = f"{INDODAX_DEPTH_URL}{pair_id}"
    try:
        data = requests.get(url, timeout=5).json()
        bids = data.get('buy', [])
        asks = data.get('sell', [])
        
        if not bids or not asks:
            return 0, False

        # 1. Hitung total Buy Wall di 3 tick teratas (Benteng Whale)
        buy_wall_total = 0
        for bid in bids[:3]:
            try:
                price = float(bid[0])
                vol = float(bid[1])
                buy_wall_total += price * vol
            except (IndexError, ValueError, TypeError):
                continue

        # 2. Hitung Ketebalan Antrean Jual sampai target harga +30%
        target_price_30pct = current_price * 1.30
        ask_depth_30pct = 0
        valid_ask_count = 0
        
        for ask in asks:
            try:
                price = float(ask[0])
                vol = float(ask[1])
                if price <= target_price_30pct:
                    ask_depth_30pct += price * vol
                    valid_ask_count += 1
                else:
                    break
            except (IndexError, ValueError, TypeError):
                continue
                
        # Syarat Thin Ask: Ada antrean jual & total nilai jual < 2x Tembok Beli
        is_thin_ask = (valid_ask_count > 0) and (ask_depth_30pct < (buy_wall_total * 2))
        
        return buy_wall_total, is_thin_ask
    except Exception:
        return 0, False

def verify_anti_spoofing(pair_id, current_buy_wall):
    """Fitur Anti-Spoofing: Verifikasi ketahanan tembok minimal 2x pindaian beruntun."""
    global buy_wall_tracker
    now = time.time()
    
    if pair_id not in buy_wall_tracker:
        buy_wall_tracker[pair_id] = {'count': 1, 'last_val': current_buy_wall, 'last_seen': now}
        return False
    
    prev = buy_wall_tracker[pair_id]
    # Jika tembok masih bertahan (minimal 80% dari nilai pindaian awal)
    if current_buy_wall >= (prev['last_val'] * 0.8):
        buy_wall_tracker[pair_id]['count'] += 1
        buy_wall_tracker[pair_id]['last_val'] = current_buy_wall
        buy_wall_tracker[pair_id]['last_seen'] = now
    else:
        # Tembok tergerus / ditarik (Reset hitungan)
        buy_wall_tracker[pair_id] = {'count': 1, 'last_val': current_buy_wall, 'last_seen': now}
        return False

    return buy_wall_tracker[pair_id]['count'] >= 2

def analyze_trades_haka(pair_id):
    """Menghitung akumulasi HAKA vs HAKI 5 menit terakhir (300 detik)."""
    url = f"{INDODAX_TRADES_URL}{pair_id}"
    try:
        trades = requests.get(url, timeout=5).json()
        if not isinstance(trades, list):
            return 0, False

        now = time.time()
        five_minutes_ago = now - 300
        
        haka_vol = 0
        haki_vol = 0
        
        for trade in trades:
            try:
                trade_time = float(trade.get('date', 0))
                if trade_time >= five_minutes_ago:
                    price = float(trade.get('price', 0))
                    amount = float(trade.get('amount', 0))
                    vol = price * amount
                    
                    trade_type = str(trade.get('type', '')).lower()
                    if trade_type == 'buy':
                        haka_vol += vol
                    elif trade_type == 'sell':
                        haki_vol += vol
                else:
                    break
            except (ValueError, TypeError):
                continue
                
        # Dominasi HAKA: Volume >= MIN_HAKA dan minimal 2x dari HAKI (atau HAKI = 0)
        is_dominant_haka = (haka_vol >= MIN_HAKA_5M_IDR) and (haki_vol == 0 or haka_vol >= (haki_vol * 2))
        return haka_vol, is_dominant_haka
    except Exception:
        return 0, False

def run_scanner():
    print("\n==================================================")
    print("  INDODAX SPOT WHALE SCANNER (ACCURATE & RUNNING) ")
    print("==================================================")
    
    while True:
        try:
            clean_expired_spoof_tracker() # Bersihkan memori usang
            pairs = get_filtered_pairs()
            valid_signals = []

            for pair in pairs:
                pair_id = pair['id']
                symbol = pair['symbol']
                price = pair['price']
                
                time.sleep(0.15)  # Smart Queue Throttling (Bebas Blokir HTTP 429)

                # 1. Cek Order Book (Buy Wall & Thin Ask)
                buy_wall_idr, is_thin_ask = analyze_order_book(pair_id, price)
                if buy_wall_idr < MIN_BUY_WALL_IDR or not is_thin_ask:
                    continue

                # 2. Verifikasi Anti-Spoofing (Tembok Asli)
                if not verify_anti_spoofing(pair_id, buy_wall_idr):
                    continue

                # 3. Cek Akumulasi HAKA 5 Menit
                haka_vol, is_valid_haka = analyze_trades_haka(pair_id)
                if not is_valid_haka:
                    continue

                # 4. Format Sinyal Valid untuk Dasbor
                signal_data = {
                    'symbol': symbol,
                    'price_idr': price,
                    'buy_wall_idr': round(buy_wall_idr),
                    'haka_5m_idr': round(haka_vol),
                    'potential': '≥ 30%',
                    'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
                }
                valid_signals.append(signal_data)
                print(f"🔥 [SIGNAL] {symbol} | Price: Rp {price:,.0f} | Wall: Rp {buy_wall_idr:,.0f} | HAKA: Rp {haka_vol:,.0f}")

            # Ekspor hasil pindaian ke file JSON
            with open('signals.json', 'w') as f:
                json.dump(valid_signals, f, indent=4)
                
            print(f"[{time.strftime('%H:%M:%S')}] Pindaian selesai. {len(valid_signals)} sinyal tersimpan ke signals.json.")
            time.sleep(10)
            
        except KeyboardInterrupt:
            print("\n[STOP] Pemindaian dihentikan.")
            break
        except Exception as e:
            print(f"[ERROR] System loop Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    run_scanner()
