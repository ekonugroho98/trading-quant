"""
Additional Validation Metrics Module
Implementasi metrics validasi tambahan untuk trading quant
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional


def calculate_maximum_drawdown(equity_curve: pd.Series) -> Dict:
    """
    Calculate maximum drawdown
    
    Args:
        equity_curve: Series dengan cumulative returns atau equity values
    
    Returns:
        Dictionary dengan max drawdown metrics
    """
    # Calculate running maximum
    running_max = equity_curve.expanding().max()
    
    # Calculate drawdown
    drawdown = (equity_curve - running_max) / running_max
    
    # Maximum drawdown
    max_dd = drawdown.min()
    max_dd_idx = drawdown.idxmin()
    
    # Get numeric position of max_dd_idx
    try:
        max_dd_pos = equity_curve.index.get_loc(max_dd_idx)
    except (KeyError, TypeError):
        # Fallback: find position manually
        max_dd_pos = list(equity_curve.index).index(max_dd_idx) if max_dd_idx in equity_curve.index else len(equity_curve) - 1
    
    # Find peak before drawdown
    peak_idx = equity_curve[:max_dd_idx].idxmax()
    peak_value = equity_curve.loc[peak_idx]
    
    # Find recovery point (if any)
    recovery_idx = None
    if max_dd_pos < len(equity_curve) - 1:
        recovery_data = equity_curve[max_dd_idx:]
        recovery_values = recovery_data[recovery_data >= peak_value]
        if len(recovery_values) > 0:
            recovery_idx = recovery_values.index[0]
    
    # Calculate drawdown duration
    drawdown_duration = None
    try:
        if isinstance(max_dd_idx, pd.Timestamp) and isinstance(peak_idx, pd.Timestamp):
            duration = max_dd_idx - peak_idx
            if hasattr(duration, 'days'):
                drawdown_duration = duration.days
            elif hasattr(duration, 'total_seconds'):
                # For intraday data, convert to days
                drawdown_duration = duration.total_seconds() / 86400
    except (TypeError, AttributeError):
        # If not Timestamp, calculate as number of periods
        try:
            peak_pos = equity_curve.index.get_loc(peak_idx)
            drawdown_duration = max_dd_pos - peak_pos
        except (KeyError, TypeError):
            pass
    
    return {
        'max_drawdown': max_dd,
        'max_drawdown_pct': max_dd * 100,
        'drawdown_start': peak_idx,
        'drawdown_end': max_dd_idx,
        'recovery_date': recovery_idx,
        'drawdown_duration': drawdown_duration
    }


def calculate_win_rate(trades: pd.DataFrame) -> Dict:
    """
    Calculate win rate and trade statistics
    
    Args:
        trades: DataFrame dengan kolom 'profit' atau 'return'
    
    Returns:
        Dictionary dengan win rate metrics
    """
    if 'profit' in trades.columns:
        profits = trades['profit']
    elif 'return' in trades.columns:
        profits = trades['return']
    else:
        return {}
    
    winning_trades = profits[profits > 0]
    losing_trades = profits[profits < 0]
    
    total_trades = len(profits)
    win_count = len(winning_trades)
    loss_count = len(losing_trades)
    
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0
    
    avg_win = winning_trades.mean() if len(winning_trades) > 0 else 0
    avg_loss = abs(losing_trades.mean()) if len(losing_trades) > 0 else 0
    
    profit_factor = (winning_trades.sum() / abs(losing_trades.sum())) if len(losing_trades) > 0 and losing_trades.sum() != 0 else 0
    
    return {
        'win_rate': win_rate,
        'total_trades': total_trades,
        'winning_trades': win_count,
        'losing_trades': loss_count,
        'avg_winning_trade': avg_win,
        'avg_losing_trade': avg_loss,
        'profit_factor': profit_factor,
        'largest_win': winning_trades.max() if len(winning_trades) > 0 else 0,
        'largest_loss': losing_trades.min() if len(losing_trades) > 0 else 0
    }


def calculate_profit_per_trade(strategy_returns: pd.Series, 
                               signals: pd.Series) -> Dict:
    """
    Calculate profit per trade from strategy returns
    
    Args:
        strategy_returns: Series dengan strategy returns
        signals: Series dengan trading signals (1=buy, -1=sell, 0=neutral)
    
    Returns:
        Dictionary dengan profit per trade metrics
    """
    # Extract trades from signals
    trades = []
    position = 0
    entry_price = None
    
    for idx, signal in signals.items():
        if signal != 0 and position == 0:  # Entry
            position = signal
            entry_price = strategy_returns.loc[idx] if idx in strategy_returns.index else None
        elif (signal == -position) or (signal == 0 and position != 0):  # Exit
            if entry_price is not None and idx in strategy_returns.index:
                exit_price = strategy_returns.loc[idx]
                profit = (exit_price - entry_price) * position
                trades.append({
                    'entry': entry_price,
                    'exit': exit_price,
                    'profit': profit,
                    'return': profit / entry_price if entry_price != 0 else 0
                })
            position = 0
            entry_price = None
    
    if len(trades) == 0:
        return {
            'avg_profit_per_trade': 0,
            'total_trades': 0,
            'total_profit': 0
        }
    
    trades_df = pd.DataFrame(trades)
    
    return {
        'avg_profit_per_trade': trades_df['profit'].mean(),
        'total_trades': len(trades),
        'total_profit': trades_df['profit'].sum(),
        'median_profit': trades_df['profit'].median(),
        'std_profit': trades_df['profit'].std()
    }


def time_in_market_analysis(signals: pd.Series) -> Dict:
    """
    Analyze time spent in market
    
    Args:
        signals: Series dengan trading signals
    
    Returns:
        Dictionary dengan time in market metrics
    """
    total_periods = len(signals)
    in_market_periods = (signals != 0).sum()
    out_of_market_periods = (signals == 0).sum()
    
    time_in_market_pct = (in_market_periods / total_periods * 100) if total_periods > 0 else 0
    
    # Average holding period
    holding_periods = []
    current_hold = 0
    
    for signal in signals:
        if signal != 0:
            current_hold += 1
        else:
            if current_hold > 0:
                holding_periods.append(current_hold)
            current_hold = 0
    
    if current_hold > 0:
        holding_periods.append(current_hold)
    
    avg_holding_period = np.mean(holding_periods) if len(holding_periods) > 0 else 0
    
    return {
        'time_in_market_pct': time_in_market_pct,
        'time_out_of_market_pct': 100 - time_in_market_pct,
        'in_market_periods': in_market_periods,
        'out_of_market_periods': out_of_market_periods,
        'avg_holding_period': avg_holding_period,
        'max_holding_period': max(holding_periods) if len(holding_periods) > 0 else 0
    }


def walk_forward_analysis(df: pd.DataFrame, 
                          train_window: int = 100,
                          test_window: int = 20,
                          step_size: int = 20) -> Dict:
    """
    Perform walk-forward analysis
    
    Args:
        df: DataFrame dengan strategy returns
        train_window: Training window size
        test_window: Testing window size
        step_size: Step size for rolling window
    
    Returns:
        Dictionary dengan walk-forward results
    """
    if 'Strategy_Return' not in df.columns:
        return {}
    
    results = []
    
    for start_idx in range(0, len(df) - train_window - test_window, step_size):
        train_end = start_idx + train_window
        test_start = train_end
        test_end = test_start + test_window
        
        if test_end > len(df):
            break
        
        train_data = df.iloc[start_idx:train_end]
        test_data = df.iloc[test_start:test_end]
        
        # Calculate metrics for training period
        train_return = (train_data['Strategy_Return'].sum() * 100) if 'Strategy_Return' in train_data.columns else 0
        
        # Calculate metrics for testing period
        test_return = (test_data['Strategy_Return'].sum() * 100) if 'Strategy_Return' in test_data.columns else 0
        
        results.append({
            'train_start': train_data.index[0],
            'train_end': train_data.index[-1],
            'test_start': test_data.index[0],
            'test_end': test_data.index[-1],
            'train_return': train_return,
            'test_return': test_return,
            'consistency': 1 if (train_return > 0 and test_return > 0) or (train_return < 0 and test_return < 0) else 0
        })
    
    if len(results) == 0:
        return {}
    
    results_df = pd.DataFrame(results)
    
    return {
        'total_windows': len(results),
        'avg_train_return': results_df['train_return'].mean(),
        'avg_test_return': results_df['test_return'].mean(),
        'consistency_rate': results_df['consistency'].mean() * 100,
        'positive_test_windows': (results_df['test_return'] > 0).sum(),
        'negative_test_windows': (results_df['test_return'] < 0).sum()
    }


def get_all_validation_metrics(df: pd.DataFrame, 
                               equity_curve: Optional[pd.Series] = None,
                               signals: Optional[pd.Series] = None) -> Dict:
    """
    Get all validation metrics
    
    Args:
        df: DataFrame dengan strategy data
        equity_curve: Optional equity curve series
        signals: Optional signals series
    
    Returns:
        Dictionary dengan semua validation metrics
    """
    metrics = {}
    
    # Maximum drawdown
    if equity_curve is not None:
        metrics['max_drawdown'] = calculate_maximum_drawdown(equity_curve)
    elif 'Cumulative_Strategy' in df.columns:
        metrics['max_drawdown'] = calculate_maximum_drawdown(df['Cumulative_Strategy'])
    
    # Win rate (if we have trade data)
    if 'Strategy_Return' in df.columns:
        strategy_returns = df['Strategy_Return']
        trades = pd.DataFrame({
            'profit': strategy_returns[strategy_returns != 0]
        })
        if len(trades) > 0:
            metrics['win_rate'] = calculate_win_rate(trades)
    
    # Profit per trade
    if signals is not None and 'Strategy_Return' in df.columns:
        metrics['profit_per_trade'] = calculate_profit_per_trade(
            df['Strategy_Return'], signals
        )
    
    # Time in market
    if signals is not None:
        metrics['time_in_market'] = time_in_market_analysis(signals)
    elif 'Signal' in df.columns:
        metrics['time_in_market'] = time_in_market_analysis(df['Signal'])
    
    # Walk-forward analysis
    if len(df) > 200:  # Need enough data
        metrics['walk_forward'] = walk_forward_analysis(df)
    
    return metrics

