#!/usr/bin/env python3
"""
Test koneksi ke Binance API
Menggunakan python-binance library untuk mengakses Binance API
"""

import sys
from typing import Optional, Dict, Any

try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException, BinanceRequestException
except ImportError:
    print("❌ Library python-binance tidak ditemukan!")
    print("📦 Install dengan: pip install python-binance")
    sys.exit(1)

# Import config
try:
    from config import BINANCE_API_KEY, BINANCE_API_SECRET
except ImportError:
    print("⚠️  Config tidak ditemukan, menggunakan environment variables atau None")
    BINANCE_API_KEY = None
    BINANCE_API_SECRET = None


def test_binance_connection(api_key: Optional[str] = None, api_secret: Optional[str] = None) -> Dict[str, Any]:
    """
    Test koneksi ke Binance API
    
    Args:
        api_key: Binance API Key (optional, bisa dari config atau env)
        api_secret: Binance API Secret (optional, bisa dari config atau env)
    
    Returns:
        Dictionary dengan hasil test:
        {
            'success': bool,
            'message': str,
            'server_time': Optional[str],
            'account_info': Optional[Dict],
            'error': Optional[str]
        }
    """
    result = {
        'success': False,
        'message': '',
        'server_time': None,
        'account_info': None,
        'error': None
    }
    
    # Gunakan parameter atau dari config
    api_key = api_key or BINANCE_API_KEY
    api_secret = api_secret or BINANCE_API_SECRET
    
    if not api_key or not api_secret:
        result['message'] = "⚠️  API Key atau API Secret tidak ditemukan"
        result['error'] = "Missing API credentials"
        return result
    
    try:
        print("🔌 Menghubungkan ke Binance API...")
        print(f"📝 API Key: {api_key[:10]}...{api_key[-4:] if len(api_key) > 14 else ''}")
        
        # Initialize client
        # Testnet: https://testnet.binance.vision
        # Production: https://api.binance.com (default)
        client = Client(api_key, api_secret)
        
        # Test 1: Get server time (public endpoint, tidak perlu auth)
        print("\n📡 Test 1: Get Server Time (Public Endpoint)...")
        server_time = client.get_server_time()
        result['server_time'] = server_time
        print(f"✅ Server Time: {server_time}")
        
        # Test 2: Get account info (private endpoint, perlu auth)
        print("\n📡 Test 2: Get Account Info (Private Endpoint)...")
        account_info = client.get_account()
        result['account_info'] = {
            'canTrade': account_info.get('canTrade'),
            'canWithdraw': account_info.get('canWithdraw'),
            'canDeposit': account_info.get('canDeposit'),
            'balances': len(account_info.get('balances', [])),
            'total_balances': sum(1 for b in account_info.get('balances', []) if float(b.get('free', 0)) > 0 or float(b.get('locked', 0)) > 0)
        }
        print(f"✅ Account Info:")
        print(f"   - Can Trade: {result['account_info']['canTrade']}")
        print(f"   - Can Withdraw: {result['account_info']['canWithdraw']}")
        print(f"   - Can Deposit: {result['account_info']['canDeposit']}")
        print(f"   - Total Balances: {result['account_info']['total_balances']} assets")
        
        # Test 3: Get exchange info (public endpoint)
        print("\n📡 Test 3: Get Exchange Info (Public Endpoint)...")
        exchange_info = client.get_exchange_info()
        symbols_count = len(exchange_info.get('symbols', []))
        print(f"✅ Exchange Info: {symbols_count} trading pairs available")
        
        # Test 4: Get 24h ticker (public endpoint)
        print("\n📡 Test 4: Get 24h Ticker for BTCUSDT (Public Endpoint)...")
        ticker = client.get_symbol_ticker(symbol="BTCUSDT")
        print(f"✅ BTCUSDT Price: ${float(ticker['price']):,.2f}")
        
        result['success'] = True
        result['message'] = "✅ Koneksi ke Binance API berhasil!"
        
        return result
        
    except BinanceAPIException as e:
        error_msg = f"Binance API Error: {e.status_code} - {e.message}"
        print(f"❌ {error_msg}")
        result['error'] = error_msg
        result['message'] = f"❌ Error dari Binance API: {e.message}"
        return result
        
    except BinanceRequestException as e:
        error_msg = f"Binance Request Error: {e.status_code} - {e.message}"
        print(f"❌ {error_msg}")
        result['error'] = error_msg
        result['message'] = f"❌ Error request ke Binance: {e.message}"
        return result
        
    except Exception as e:
        error_msg = f"Unexpected Error: {type(e).__name__}: {str(e)}"
        print(f"❌ {error_msg}")
        result['error'] = error_msg
        result['message'] = f"❌ Error tidak terduga: {str(e)}"
        return result


def test_public_endpoints_only():
    """
    Test koneksi ke Binance API tanpa autentikasi (hanya public endpoints)
    Berguna untuk test koneksi dasar tanpa perlu API key
    """
    result = {
        'success': False,
        'message': '',
        'server_time': None,
        'error': None
    }
    
    try:
        print("🔌 Menghubungkan ke Binance API (Public Endpoints Only)...")
        
        # Initialize client tanpa API key (hanya untuk public endpoints)
        # Tambahkan timeout dan retry untuk koneksi yang lebih stabil
        # Note: verify=False hanya untuk testing, jangan gunakan di production!
        import ssl
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        client = Client(requests_params={'timeout': 10, 'verify': False})
        
        # Test: Get server time
        print("\n📡 Test: Get Server Time...")
        try:
            server_time = client.get_server_time()
            result['server_time'] = server_time
            print(f"✅ Server Time: {server_time}")
        except Exception as e:
            print(f"⚠️  Error getting server time: {e}")
            # Coba lagi dengan request langsung
            import requests
            try:
                response = requests.get('https://api.binance.com/api/v3/time', timeout=10)
                if response.status_code == 200:
                    server_time = response.json()
                    result['server_time'] = server_time
                    print(f"✅ Server Time (via requests): {server_time}")
                else:
                    raise Exception(f"HTTP {response.status_code}")
            except Exception as e2:
                raise Exception(f"Both methods failed: {e}, {e2}")
        
        # Test: Get exchange info
        print("\n📡 Test: Get Exchange Info...")
        exchange_info = client.get_exchange_info()
        symbols_count = len(exchange_info.get('symbols', []))
        print(f"✅ Exchange Info: {symbols_count} trading pairs available")
        
        # Test: Get BTC price
        print("\n📡 Test: Get BTCUSDT Price...")
        ticker = client.get_symbol_ticker(symbol="BTCUSDT")
        btc_price = float(ticker['price'])
        print(f"✅ BTCUSDT Price: ${btc_price:,.2f}")
        
        result['success'] = True
        result['message'] = "✅ Koneksi ke Binance API (Public) berhasil!"
        
        return result
        
    except BinanceAPIException as e:
        error_msg = f"Binance API Error: {e.status_code} - {e.message}"
        print(f"❌ {error_msg}")
        result['error'] = error_msg
        result['message'] = f"❌ Error dari Binance API: {e.message}"
        return result
        
    except BinanceRequestException as e:
        error_msg = f"Binance Request Error: {e.status_code} - {e.message}"
        print(f"❌ {error_msg}")
        result['error'] = error_msg
        result['message'] = f"❌ Error request ke Binance: {e.message}"
        return result
        
    except Exception as e:
        error_msg = f"Error: {type(e).__name__}: {str(e)}"
        print(f"❌ {error_msg}")
        result['error'] = error_msg
        result['message'] = f"❌ Error: {str(e)}"
        import traceback
        print(f"📋 Traceback:")
        traceback.print_exc()
        return result


if __name__ == "__main__":
    print("=" * 70)
    print("🧪 TEST KONEKSI BINANCE API")
    print("=" * 70)
    print()
    
    # Test 1: Public endpoints (tidak perlu API key)
    print("📋 Test 1: Public Endpoints (No Auth Required)")
    print("-" * 70)
    public_result = test_public_endpoints_only()
    print(f"\n{public_result['message']}")
    print()
    
    # Test 2: Private endpoints (perlu API key)
    if BINANCE_API_KEY and BINANCE_API_SECRET:
        print("📋 Test 2: Private Endpoints (Auth Required)")
        print("-" * 70)
        private_result = test_binance_connection()
        print(f"\n{private_result['message']}")
    else:
        print("📋 Test 2: Private Endpoints (Auth Required)")
        print("-" * 70)
        print("⚠️  API Key atau API Secret tidak ditemukan di config.py")
        print("💡 Tambahkan BINANCE_API_KEY dan BINANCE_API_SECRET ke config.py untuk test private endpoints")
        print()
        print("📝 Contoh di config.py:")
        print("   BINANCE_API_KEY = 'your_api_key_here'")
        print("   BINANCE_API_SECRET = 'your_api_secret_here'")
    
    print()
    print("=" * 70)
    print("✅ Test selesai!")
    print("=" * 70)

