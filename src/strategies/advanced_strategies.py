"""
Advanced Trading Strategies Module
Implementasi Pairs Trading, Statistical Arbitrage, Grid Trading, dan DCA
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


def pairs_trading_strategy(price1: pd.Series, 
                          price2: pd.Series,
                          entry_threshold: float = 2.0,
                          exit_threshold: float = 0.5,
                          stop_loss_pct: float = 3.0,
                          long_only: bool = True) -> Dict:
    """
    Pairs Trading Strategy berdasarkan cointegration
    
    Args:
        price1: Price series untuk asset 1
        price2: Price series untuk asset 2
        entry_threshold: Z-score threshold untuk entry
        exit_threshold: Z-score threshold untuk exit
        stop_loss_pct: Stop loss percentage
        long_only: True = long-only (untuk spot trading), False = long-short (untuk futures)
    
    Returns:
        Dictionary dengan strategy results
    """
    try:
        from src.analysis.cointegration_analysis import calculate_cointegration, calculate_spread_signals
    except ImportError:
        print("⚠️  cointegration_analysis tidak tersedia")
        return {}
    
    # Calculate cointegration
    coint_result = calculate_cointegration(price1, price2)
    
    if not coint_result or not coint_result.get('cointegrated', False):
        print("⚠️  Pairs tidak cointegrated, tidak bisa menggunakan pairs trading")
        return {}
    
    spread = coint_result['spread']
    hedge_ratio = coint_result['hedge_ratio']
    intercept = coint_result['intercept']
    
    # Calculate signals
    signals = calculate_spread_signals(spread, entry_threshold, exit_threshold)
    
    # Calculate positions
    position1 = pd.Series(0.0, index=price1.index)
    position2 = pd.Series(0.0, index=price2.index)
    
    if long_only:
        # Long-only version untuk spot trading
        # Long asset yang undervalued (spread z-score < -entry_threshold)
        # Exit ketika spread kembali normal (z-score > -exit_threshold)
        
        # When spread is low (asset2 undervalued relative to asset1): long asset2
        # When spread is high (asset1 undervalued relative to asset2): long asset1
        spread_mean = spread.mean()
        spread_std = spread.std()
        zscore = (spread - spread_mean) / spread_std if spread_std > 0 else pd.Series(0, index=spread.index)
        
        # Long asset2 when spread is low (asset2 undervalued)
        position2[zscore < -entry_threshold] = 1.0
        
        # Long asset1 when spread is high (asset1 undervalued)
        position1[zscore > entry_threshold] = 1.0
        
        # Exit when spread returns to normal
        position1[zscore.abs() < exit_threshold] = 0.0
        position2[zscore.abs() < exit_threshold] = 0.0
    else:
        # Long-short version untuk futures trading
        # Long spread = long asset2, short asset1 (with hedge ratio)
        # Short spread = short asset2, long asset1 (with hedge ratio)
        
        # When signal = 1 (long spread): long asset2, short asset1
        position1[signals == 1] = -1.0  # Short asset1
        position2[signals == 1] = 1.0   # Long asset2
        
        # When signal = -1 (short spread): short asset2, long asset1
        position1[signals == -1] = 1.0   # Long asset1
        position2[signals == -1] = -1.0  # Short asset2
    
    # Calculate returns
    returns1 = price1.pct_change()
    returns2 = price2.pct_change()
    
    # Strategy return = weighted combination of both positions
    if long_only:
        # Long-only: simple weighted return
        strategy_return = (position1.shift(1) * returns1 + 
                          position2.shift(1) * returns2)
    else:
        # Long-short: include hedge ratio
        strategy_return = (position1.shift(1) * returns1 + 
                          position2.shift(1) * returns2 * hedge_ratio)
    
    # Calculate cumulative returns
    cumulative_return = (1 + strategy_return).cumprod()
    
    # Calculate metrics
    total_return = cumulative_return.iloc[-1] - 1 if len(cumulative_return) > 0 else 0
    
    return {
        'strategy_name': 'Pairs Trading',
        'cointegrated': True,
        'hedge_ratio': hedge_ratio,
        'signals': signals,
        'position1': position1,
        'position2': position2,
        'strategy_return': strategy_return,
        'cumulative_return': cumulative_return,
        'total_return': total_return,
        'spread': spread,
        'coint_result': coint_result
    }


def statistical_arbitrage_strategy(price_data: Dict[str, pd.Series],
                                   entry_threshold: float = 2.0,
                                   exit_threshold: float = 0.5,
                                   min_correlation: float = 0.7,
                                   long_only: bool = True) -> Dict:
    """
    Statistical Arbitrage Strategy menggunakan mean reversion pada multiple assets
    
    Args:
        price_data: Dictionary dengan symbol -> price series
        entry_threshold: Z-score threshold untuk entry
        exit_threshold: Z-score threshold untuk exit
        min_correlation: Minimum correlation untuk inclusion
        long_only: True = long-only (untuk spot trading), False = long-short (untuk futures)
    
    Returns:
        Dictionary dengan strategy results
    """
    if len(price_data) < 2:
        print("⚠️  Statistical arbitrage membutuhkan minimal 2 assets")
        return {}
    
    # Find highly correlated pairs
    symbols = list(price_data.keys())
    correlated_pairs = []
    
    for i in range(len(symbols)):
        for j in range(i + 1, len(symbols)):
            symbol1 = symbols[i]
            symbol2 = symbols[j]
            
            corr = price_data[symbol1].corr(price_data[symbol2])
            if abs(corr) >= min_correlation:
                correlated_pairs.append({
                    'pair': (symbol1, symbol2),
                    'correlation': corr
                })
    
    if len(correlated_pairs) == 0:
        print("⚠️  Tidak ada pairs dengan correlation >= {min_correlation}")
        return {}
    
    # Use first pair for strategy (can be extended to multiple pairs)
    best_pair = correlated_pairs[0]
    symbol1, symbol2 = best_pair['pair']
    
    price1 = price_data[symbol1]
    price2 = price_data[symbol2]
    
    # Calculate ratio
    ratio = price1 / price2
    
    # Calculate z-score of ratio
    ratio_mean = ratio.rolling(window=20).mean()
    ratio_std = ratio.rolling(window=20).std()
    zscore = (ratio - ratio_mean) / ratio_std
    
    # Generate signals
    signals = pd.Series(0, index=price1.index)
    
    if long_only:
        # Long-only version untuk spot trading
        # Long asset1 ketika ratio rendah (asset1 undervalued)
        # Long asset2 ketika ratio tinggi (asset2 undervalued)
        # Exit ketika ratio kembali normal
        signals[zscore < -entry_threshold] = 1   # Long asset1 (ratio rendah)
        signals[zscore > entry_threshold] = 2      # Long asset2 (ratio tinggi, berarti asset2 undervalued)
        signals[zscore.abs() < exit_threshold] = 0  # Exit
    else:
        # Long-short version untuk futures trading
        signals[zscore < -entry_threshold] = 1   # Long ratio (long asset1, short asset2)
        signals[zscore > entry_threshold] = -1   # Short ratio (short asset1, long asset2)
        signals[zscore.abs() < exit_threshold] = 0  # Exit
    
    # Calculate returns
    returns1 = price1.pct_change()
    returns2 = price2.pct_change()
    
    # Strategy return
    if long_only:
        # Long-only: long asset yang undervalued
        strategy_return = pd.Series(0.0, index=price1.index)
        strategy_return[signals == 1] = returns1[signals == 1]  # Long asset1
        strategy_return[signals == 2] = returns2[signals == 2]  # Long asset2
    else:
        # Long-short: long-short portfolio
        strategy_return = (signals.shift(1) * (returns1 - returns2))
    
    cumulative_return = (1 + strategy_return).cumprod()
    total_return = cumulative_return.iloc[-1] - 1 if len(cumulative_return) > 0 else 0
    
    return {
        'strategy_name': 'Statistical Arbitrage',
        'pairs_used': correlated_pairs,
        'signals': signals,
        'strategy_return': strategy_return,
        'cumulative_return': cumulative_return,
        'total_return': total_return,
        'ratio': ratio,
        'zscore': zscore
    }


def grid_trading_strategy(price: pd.Series,
                         grid_levels: int = 10,
                         grid_spacing_pct: float = 1.0,
                         initial_position: float = 0.0) -> Dict:
    """
    Grid Trading Strategy - Automated DCA dengan multiple levels
    
    Args:
        price: Price series
        grid_levels: Number of grid levels
        grid_spacing_pct: Spacing between grid levels (percentage)
        initial_position: Initial position size
    
    Returns:
        Dictionary dengan strategy results
    """
    # Calculate grid levels
    price_min = price.min()
    price_max = price.max()
    price_range = price_max - price_min
    
    grid_prices = []
    for i in range(grid_levels):
        level_price = price_min + (price_range * i / (grid_levels - 1))
        grid_prices.append(level_price)
    
    # Alternative: Use percentage-based grid
    current_price = price.iloc[-1]
    grid_prices_pct = []
    for i in range(grid_levels):
        if i < grid_levels // 2:
            # Below current price
            level_price = current_price * (1 - (grid_levels // 2 - i) * grid_spacing_pct / 100)
        else:
            # Above current price
            level_price = current_price * (1 + (i - grid_levels // 2) * grid_spacing_pct / 100)
        grid_prices_pct.append(level_price)
    
    # Use percentage-based grid
    grid_prices = sorted(grid_prices_pct)
    
    # Calculate position at each price level
    position = pd.Series(initial_position, index=price.index)
    grid_positions = {}
    
    for i, grid_price in enumerate(grid_prices):
        # Buy when price drops to grid level
        buy_signals = (price <= grid_price) & (price.shift(1) > grid_price)
        
        # Sell when price rises above grid level
        sell_signals = (price >= grid_price) & (price.shift(1) < grid_price)
        
        grid_positions[grid_price] = {
            'buy_signals': buy_signals.sum(),
            'sell_signals': sell_signals.sum()
        }
    
    # Simple grid strategy: accumulate on dips, take profit on rallies
    signals = pd.Series(0, index=price.index)
    
    for i in range(1, len(price)):
        current_price = price.iloc[i]
        prev_price = price.iloc[i-1]
        
        # Find nearest grid levels
        below_levels = [p for p in grid_prices if p < current_price]
        above_levels = [p for p in grid_prices if p > current_price]
        
        # Buy signal: price dropped to a grid level
        if below_levels and prev_price > max(below_levels) and current_price <= max(below_levels):
            signals.iloc[i] = 1  # Buy
        
        # Sell signal: price rose above a grid level
        if above_levels and prev_price < min(above_levels) and current_price >= min(above_levels):
            signals.iloc[i] = -1  # Sell
    
    # Calculate returns
    returns = price.pct_change()
    strategy_return = signals.shift(1) * returns
    
    cumulative_return = (1 + strategy_return).cumprod()
    total_return = cumulative_return.iloc[-1] - 1 if len(cumulative_return) > 0 else 0
    
    return {
        'strategy_name': 'Grid Trading',
        'grid_levels': grid_levels,
        'grid_prices': grid_prices,
        'grid_positions': grid_positions,
        'signals': signals,
        'strategy_return': strategy_return,
        'cumulative_return': cumulative_return,
        'total_return': total_return
    }


def dca_strategy(price: pd.Series,
                investment_amount: float = 100.0,
                frequency: int = 7) -> Dict:
    """
    Dollar Cost Averaging (DCA) Strategy
    
    Args:
        price: Price series
        investment_amount: Amount to invest per period
        frequency: Investment frequency (every N periods)
    
    Returns:
        Dictionary dengan strategy results
    """
    # Calculate investment dates
    investment_dates = price.index[::frequency]
    
    # Calculate shares bought at each date
    shares_bought = pd.Series(0.0, index=price.index)
    total_shares = 0.0
    total_invested = 0.0
    
    for date in investment_dates:
        if date in price.index:
            price_at_date = price.loc[date]
            shares = investment_amount / price_at_date
            shares_bought.loc[date] = shares
            total_shares += shares
            total_invested += investment_amount
    
    # Calculate cumulative shares
    cumulative_shares = shares_bought.cumsum()
    
    # Calculate portfolio value over time
    portfolio_value = cumulative_shares * price
    
    # Calculate returns
    initial_value = total_invested
    final_value = portfolio_value.iloc[-1] if len(portfolio_value) > 0 else initial_value
    total_return = (final_value - initial_value) / initial_value if initial_value > 0 else 0
    
    # Calculate cost basis
    cost_basis = pd.Series(total_invested, index=price.index)
    for i, date in enumerate(investment_dates):
        if date in cost_basis.index:
            cost_basis.loc[date:] = (i + 1) * investment_amount
    
    return {
        'strategy_name': 'Dollar Cost Averaging',
        'investment_amount': investment_amount,
        'frequency': frequency,
        'total_invested': total_invested,
        'total_shares': total_shares,
        'final_value': final_value,
        'total_return': total_return,
        'shares_bought': shares_bought,
        'cumulative_shares': cumulative_shares,
        'portfolio_value': portfolio_value,
        'cost_basis': cost_basis
    }


def print_strategy_results(results: Dict):
    """Print strategy results"""
    if not results:
        return
    
    strategy_name = results.get('strategy_name', 'Unknown')
    
    print("\n" + "=" * 70)
    print(f"📊 {strategy_name.upper()} RESULTS")
    print("=" * 70)
    
    total_return = results.get('total_return', 0)
    print(f"\n💰 Total Return: {total_return*100:.2f}%")
    
    if 'cumulative_return' in results:
        cum_ret = results['cumulative_return']
        if len(cum_ret) > 0:
            print(f"   Final Cumulative Return: {cum_ret.iloc[-1]:.4f}")
    
    if 'signals' in results:
        signals = results['signals']
        buy_count = (signals == 1).sum()
        sell_count = (signals == -1).sum()
        print(f"\n📈 Signals Generated:")
        print(f"   Buy Signals: {buy_count}")
        print(f"   Sell Signals: {sell_count}")
    
    print("\n" + "=" * 70)

