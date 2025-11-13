"""
DeepSeek API Integration Module
Mengirim data analisis ke DeepSeek AI untuk mendapatkan rekomendasi trading
"""

import json
import requests
from typing import Dict, Optional, Any
from datetime import datetime


class DeepSeekTradingAdvisor:
    """Class untuk integrasi dengan DeepSeek API untuk trading advice"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.deepseek.com"):
        """
        Initialize DeepSeek API client
        
        Args:
            api_key: DeepSeek API key (optional, bisa dari config)
            base_url: Base URL untuk DeepSeek API
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.endpoint = f"{self.base_url}/v1/chat/completions"
    
    def prepare_analysis_data(self, analysis_results: Dict) -> str:
        """
        Prepare analysis data untuk dikirim ke AI
        
        Args:
            analysis_results: Dictionary dengan semua hasil analisis
        
        Returns:
            Formatted string untuk prompt
        """
        prompt_parts = []
        
        # Basic Info
        if 'basic_info' in analysis_results:
            basic = analysis_results['basic_info']
            prompt_parts.append("=== INFORMASI DASAR ===")
            prompt_parts.append(f"Symbol: {basic.get('symbol', 'N/A')}")
            prompt_parts.append(f"Trading Style: {basic.get('trading_style', 'N/A')}")
            prompt_parts.append(f"Interval: {basic.get('interval', 'N/A')}")
            prompt_parts.append(f"Total Records: {basic.get('total_records', 'N/A')}")
            prompt_parts.append(f"Period: {basic.get('period', 'N/A')}")
            prompt_parts.append("")
        
        # Current Position
        if 'current_position' in analysis_results:
            pos = analysis_results['current_position']
            prompt_parts.append("=== POSISI SAAT INI ===")
            prompt_parts.append(f"Position: {pos.get('position', 'N/A')}")
            prompt_parts.append(f"Current Price: {pos.get('current_price', 'N/A')}")
            prompt_parts.append(f"MA Short: {pos.get('ma_short', 'N/A')}")
            prompt_parts.append(f"MA Long: {pos.get('ma_long', 'N/A')}")
            prompt_parts.append(f"Support: {pos.get('support', 'N/A')} (distance: {pos.get('support_distance', 'N/A')})")
            prompt_parts.append(f"Resistance: {pos.get('resistance', 'N/A')} (distance: {pos.get('resistance_distance', 'N/A')})")
            prompt_parts.append("")
        
        # Strategy Performance
        if 'strategy_performance' in analysis_results:
            perf = analysis_results['strategy_performance']
            prompt_parts.append("=== PERFORMANSI STRATEGI ===")
            prompt_parts.append(f"Buy & Hold Return: {perf.get('buy_hold_return', 'N/A')}")
            prompt_parts.append(f"Strategy Return: {perf.get('strategy_return', 'N/A')}")
            prompt_parts.append(f"Buy Periods: {perf.get('buy_periods', 'N/A')} ({perf.get('buy_periods_pct', 'N/A')})")
            prompt_parts.append(f"Sell Periods: {perf.get('sell_periods', 'N/A')} ({perf.get('sell_periods_pct', 'N/A')})")
            prompt_parts.append(f"Neutral Periods: {perf.get('neutral_periods', 'N/A')} ({perf.get('neutral_periods_pct', 'N/A')})")
            prompt_parts.append(f"Buy Signals: {perf.get('buy_signals', 'N/A')}")
            prompt_parts.append(f"Sell Signals: {perf.get('sell_signals', 'N/A')}")
            prompt_parts.append("")
        
        # Trading Setup
        if 'trading_setup' in analysis_results:
            setup = analysis_results['trading_setup']
            prompt_parts.append("=== TRADING SETUP ===")
            prompt_parts.append(f"Direction: {setup.get('direction', 'N/A')}")
            prompt_parts.append(f"Limit Entry: {setup.get('limit_entry', 'N/A')}")
            prompt_parts.append(f"Stop Loss: {setup.get('stop_loss', 'N/A')} ({setup.get('stop_loss_pct', 'N/A')})")
            if 'targets' in setup:
                for i, tp in enumerate(setup['targets'], 1):
                    prompt_parts.append(f"TP{i}: {tp.get('price', 'N/A')} ({tp.get('pct', 'N/A')})")
            if 'risk_reward' in setup:
                prompt_parts.append(f"Risk/Reward: {setup.get('risk_reward', 'N/A')}")
            prompt_parts.append("")
        
        # Volume Analysis
        if 'volume_analysis' in analysis_results:
            vol = analysis_results['volume_analysis']
            prompt_parts.append("=== VOLUME ANALYSIS ===")
            prompt_parts.append(f"VWAP: {vol.get('vwap', 'N/A')}")
            prompt_parts.append(f"Price vs VWAP: {vol.get('price_vs_vwap', 'N/A')}")
            prompt_parts.append(f"Volume Ratio: {vol.get('volume_ratio', 'N/A')}")
            prompt_parts.append(f"Volume Spikes: {vol.get('volume_spikes', 'N/A')}")
            prompt_parts.append(f"Current Volume: {vol.get('volume_class', 'N/A')}")
            prompt_parts.append("")
        
        # Market Context
        if 'market_context' in analysis_results:
            ctx = analysis_results['market_context']
            prompt_parts.append("=== MARKET CONTEXT ===")
            prompt_parts.append(f"Market Regime: {ctx.get('market_regime', 'N/A')}")
            prompt_parts.append(f"Trend Direction: {ctx.get('trend_direction', 'N/A')}")
            prompt_parts.append(f"Volatility Regime: {ctx.get('volatility_regime', 'N/A')}")
            prompt_parts.append(f"Higher TF Trend: {ctx.get('higher_tf_trend', 'N/A')}")
            prompt_parts.append("")
        
        # Advanced Features
        if 'advanced_features' in analysis_results:
            adv = analysis_results['advanced_features']
            prompt_parts.append("=== ADVANCED FEATURES ===")
            if 'z_score' in adv:
                prompt_parts.append(f"Z-Score: {adv['z_score']} {'(Overbought)' if adv['z_score'] > 2 else '(Oversold)' if adv['z_score'] < -2 else ''}")
            if 'rsi' in adv:
                prompt_parts.append(f"RSI: {adv['rsi']} {'(Overbought)' if adv['rsi'] > 70 else '(Oversold)' if adv['rsi'] < 30 else ''}")
            if 'cycle_period' in adv:
                prompt_parts.append(f"Cycle Period: {adv['cycle_period']}")
            if 'patterns' in adv:
                patterns = [p for p in adv['patterns'] if adv['patterns'][p]]
                if patterns:
                    prompt_parts.append(f"Patterns Detected: {', '.join(patterns)}")
            prompt_parts.append("")
        
        # Validation Metrics
        if 'validation_metrics' in analysis_results:
            metrics = analysis_results['validation_metrics']
            prompt_parts.append("=== VALIDATION METRICS ===")
            if 'max_drawdown' in metrics:
                prompt_parts.append(f"Max Drawdown: {metrics['max_drawdown'].get('max_drawdown_pct', 'N/A')}%")
            if 'win_rate' in metrics:
                wr = metrics['win_rate']
                prompt_parts.append(f"Win Rate: {wr.get('win_rate', 'N/A')}%")
                prompt_parts.append(f"Total Trades: {wr.get('total_trades', 'N/A')}")
                prompt_parts.append(f"Profit Factor: {wr.get('profit_factor', 'N/A')}")
            if 'walk_forward' in metrics:
                wf = metrics['walk_forward']
                prompt_parts.append(f"Walk-Forward Consistency: {wf.get('consistency_rate', 'N/A')}%")
            prompt_parts.append("")
        
        # ML Prediction
        if 'ml_prediction' in analysis_results:
            ml = analysis_results['ml_prediction']
            prompt_parts.append("=== ML PREDICTION ===")
            prompt_parts.append(f"Signal: {ml.get('signal', 'N/A')}")
            prompt_parts.append(f"Buy Probability: {ml.get('buy_prob', 'N/A')}")
            prompt_parts.append(f"Sell Probability: {ml.get('sell_prob', 'N/A')}")
            prompt_parts.append(f"Accuracy: {ml.get('accuracy', 'N/A')}")
            prompt_parts.append(f"Expected Value: {ml.get('expected_value', 'N/A')}")
            prompt_parts.append(f"Sharpe Ratio: {ml.get('sharpe_ratio', 'N/A')}")
            prompt_parts.append("")
        
        return "\n".join(prompt_parts)
    
    def create_trading_prompt(self, analysis_data: str) -> str:
        """
        Create prompt untuk DeepSeek AI
        
        Args:
            analysis_data: Formatted analysis data
        
        Returns:
            Complete prompt string
        """
        prompt = f"""Anda adalah seorang expert quantitative trader dan technical analyst. Berdasarkan data analisis trading berikut, berikan rekomendasi trading yang tepat.

{analysis_data}

Berdasarkan semua data di atas, berikan rekomendasi trading dalam format JSON berikut:

{{
    "action": "BUY|SELL|HOLD",
    "position": "LONG|SHORT|CASH",
    "confidence": 0-100,
    "entry_price": number atau null (jika HOLD, gunakan current price sebagai referensi),
    "targets": [number] atau [] (jika HOLD, berikan 3 target potensial berdasarkan support/resistance),
    "stop_loss": number atau null (jika HOLD, gunakan support/resistance sebagai referensi),
    "reason": "string singkat menjelaskan alasan rekomendasi"
}}

PENTING:
- Jika action adalah HOLD, set entry_price, targets, dan stop_loss ke null (tidak perlu karena tidak ada posisi trading)
- Jika action adalah BUY atau SELL, entry_price, targets, dan stop_loss harus berupa number/array yang valid
- entry_price: number atau null (null jika HOLD)
- targets: array of numbers atau [] (empty array jika HOLD)
- stop_loss: number atau null (null jika HOLD)

Pertimbangkan:
1. Current position dan signal dari strategi
2. Support/Resistance levels
3. Volume analysis dan market context
4. Advanced features (RSI, Z-Score, patterns)
5. Validation metrics (win rate, drawdown, consistency)
6. ML prediction dan confidence level
7. Risk/reward ratio dari trading setup

Berikan rekomendasi yang konservatif dan berdasarkan data. Jika confidence rendah atau sinyal bertentangan, pilih HOLD dengan position CASH, tapi tetap berikan entry_price, targets, dan stop_loss untuk referensi.

Hanya kembalikan JSON, tanpa penjelasan tambahan."""
        
        return prompt
    
    def call_deepseek_api(self, prompt: str, model: str = "deepseek-chat") -> Optional[Dict]:
        """
        Call DeepSeek API untuk mendapatkan rekomendasi
        
        Args:
            prompt: Prompt untuk AI
            model: Model name (default: deepseek-chat)
        
        Returns:
            Dictionary dengan response dari API atau None jika error
        """
        if not self.api_key:
            print("⚠️  DeepSeek API key tidak ditemukan")
            return None
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.3,  # Lower temperature untuk konsistensi
            "max_tokens": 500
        }
        
        try:
            response = requests.post(
                self.endpoint,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                return self.parse_ai_response(content)
            else:
                print(f"❌ Error dari DeepSeek API: {response.status_code}")
                print(f"   Response: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Error menghubungi DeepSeek API: {e}")
            return None
        except Exception as e:
            print(f"❌ Error parsing response: {e}")
            return None
    
    def parse_ai_response(self, content: str) -> Optional[Dict]:
        """
        Parse AI response dan extract JSON
        
        Args:
            content: Raw content dari AI response
        
        Returns:
            Parsed dictionary atau None jika error
        """
        try:
            # Cari JSON di dalam response (bisa ada markdown code block)
            content = content.strip()
            
            # Remove markdown code blocks jika ada
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            
            if content.endswith("```"):
                content = content[:-3]
            
            content = content.strip()
            
            # Parse JSON
            result = json.loads(content)
            
            # Validate structure
            required_fields = ['action', 'position', 'confidence', 'entry_price', 'targets', 'stop_loss', 'reason']
            
            # Check if all fields exist
            if not all(field in result for field in required_fields):
                print("⚠️  Response tidak lengkap, field yang hilang:", 
                      [f for f in required_fields if f not in result])
                return None
            
            # Handle null values - replace with defaults based on current price if available
            # Try to get current price from analysis data if available
            # For now, we'll just ensure entry_price and stop_loss are numbers
            if result.get('entry_price') is None:
                # If entry_price is null, we'll handle it in the calling function
                print("⚠️  entry_price is null in AI response")
            
            if result.get('stop_loss') is None:
                # If stop_loss is null, we'll handle it in the calling function
                print("⚠️  stop_loss is null in AI response")
            
            if not isinstance(result.get('targets'), list):
                result['targets'] = []
            
            return result
                
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing JSON: {e}")
            print(f"   Content: {content[:200]}...")
            return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def get_trading_recommendation(self, analysis_results: Dict) -> Optional[Dict]:
        """
        Main method untuk mendapatkan rekomendasi trading dari DeepSeek
        
        Args:
            analysis_results: Dictionary dengan semua hasil analisis
        
        Returns:
            Dictionary dengan rekomendasi trading atau None jika error
        """
        # Prepare data
        analysis_data = self.prepare_analysis_data(analysis_results)
        
        # Create prompt
        prompt = self.create_trading_prompt(analysis_data)
        
        # Call API
        recommendation = self.call_deepseek_api(prompt)
        
        return recommendation


def format_recommendation_output(recommendation: Dict, 
                                 current_price: Optional[float] = None,
                                 support: Optional[float] = None,
                                 resistance: Optional[float] = None,
                                 timeframe: Optional[str] = None,
                                 symbol: Optional[str] = None) -> str:
    """
    Format recommendation untuk ditampilkan
    
    Args:
        recommendation: Dictionary dengan rekomendasi
        current_price: Harga saat ini (optional)
        support: Support level (optional)
        resistance: Resistance level (optional)
        timeframe: Timeframe trading (optional)
        symbol: Trading symbol (optional)
    
    Returns:
        Formatted string
    """
    if not recommendation:
        return "❌ Tidak ada rekomendasi"
    
    output = []
    output.append("\n" + "=" * 70)
    output.append("🤖 DEEPSEEK AI TRADING RECOMMENDATION")
    output.append("=" * 70)
    
    # Symbol dan Timeframe
    if symbol:
        output.append(f"\n📊 Symbol: {symbol}")
    if timeframe:
        output.append(f"⏰ Timeframe: {timeframe}")
    
    # Tampilkan current price jika tersedia
    if current_price is not None:
        output.append(f"\n💵 Current Price: {current_price:,.2f}")
    
    # Support & Resistance
    if support is not None or resistance is not None:
        output.append(f"\n📈 Key Levels:")
        if support is not None:
            output.append(f"   🟢 Support: {support:,.2f}")
        if resistance is not None:
            output.append(f"   🔴 Resistance: {resistance:,.2f}")
    
    output.append(f"\n📊 Action: {recommendation.get('action', 'N/A')}")
    output.append(f"📍 Position: {recommendation.get('position', 'N/A')}")
    output.append(f"🎯 Confidence: {recommendation.get('confidence', 0)}%")
    
    # Trading Setup (hanya untuk BUY/SELL, tidak untuk HOLD)
    action = recommendation.get('action', '').upper()
    if action != 'HOLD':
        # Entry Price
        entry_price = recommendation.get('entry_price')
        if isinstance(entry_price, (int, float)):
            output.append(f"\n💰 Entry Price: {entry_price:,.2f}")
        else:
            output.append(f"\n💰 Entry Price: {entry_price}")
        
        # Stop Loss dengan persentase
        stop_loss = recommendation.get('stop_loss')
        if isinstance(stop_loss, (int, float)) and isinstance(entry_price, (int, float)) and entry_price > 0:
            stop_loss_pct = ((stop_loss - entry_price) / entry_price) * 100
            sign = "+" if stop_loss_pct > 0 else ""
            output.append(f"🛑 Stop Loss: {stop_loss:,.2f} ({sign}{stop_loss_pct:.2f}%)")
        elif stop_loss is not None:
            output.append(f"🛑 Stop Loss: {stop_loss}")
        
        # Targets dengan persentase
        targets = recommendation.get('targets', [])
        if targets:
            output.append(f"\n🎯 Targets:")
            for i, target in enumerate(targets, 1):
                if isinstance(target, (int, float)) and isinstance(entry_price, (int, float)) and entry_price > 0:
                    target_pct = ((target - entry_price) / entry_price) * 100
                    sign = "+" if target_pct > 0 else ""
                    output.append(f"   TP{i}: {target:,.2f} ({sign}{target_pct:.2f}%)")
                else:
                    output.append(f"   TP{i}: {target}")
    
    reason = recommendation.get('reason', '')
    if reason:
        output.append(f"\n💡 Reason: {reason}")
    
    output.append("\n" + "=" * 70)
    
    return "\n".join(output)

