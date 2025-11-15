"""
Multi-Strategy Portfolio Management Module
Mengelola multiple trading strategies dengan dynamic selection dan weighting
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


def calculate_strategy_performance(strategy_returns: pd.Series,
                                  lookback_window: int = 30) -> Dict:
    """
    Calculate strategy performance metrics
    
    Args:
        strategy_returns: Strategy returns series
        lookback_window: Lookback window untuk performance calculation
    
    Returns:
        Dictionary dengan performance metrics
    """
    if len(strategy_returns) == 0:
        return {}
    
    # Use recent data
    recent_returns = strategy_returns.tail(lookback_window)
    
    # Calculate metrics
    total_return = (1 + recent_returns).prod() - 1
    sharpe_ratio = recent_returns.mean() / recent_returns.std() * np.sqrt(252) if recent_returns.std() > 0 else 0
    win_rate = (recent_returns > 0).sum() / len(recent_returns) if len(recent_returns) > 0 else 0
    max_drawdown = calculate_max_drawdown_simple(recent_returns)
    
    return {
        'total_return': total_return,
        'sharpe_ratio': sharpe_ratio,
        'win_rate': win_rate,
        'max_drawdown': max_drawdown,
        'volatility': recent_returns.std() * np.sqrt(252),
        'avg_return': recent_returns.mean() * 252
    }


def calculate_max_drawdown_simple(returns: pd.Series) -> float:
    """Calculate simple max drawdown"""
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    return abs(drawdown.min())


def dynamic_strategy_selection(strategy_results: Dict[str, Dict],
                               selection_method: str = 'sharpe',
                               top_n: int = 3) -> List[str]:
    """
    Dynamically select best performing strategies
    
    Args:
        strategy_results: Dictionary dengan strategy_name -> strategy_results
        selection_method: Method untuk selection ('sharpe', 'return', 'win_rate', 'composite')
        top_n: Number of top strategies to select
    
    Returns:
        List of selected strategy names
    """
    strategy_scores = {}
    
    for name, results in strategy_results.items():
        if 'strategy_return' not in results:
            continue
        
        returns = results['strategy_return']
        performance = calculate_strategy_performance(returns)
        
        if selection_method == 'sharpe':
            score = performance.get('sharpe_ratio', 0)
        elif selection_method == 'return':
            score = performance.get('total_return', 0)
        elif selection_method == 'win_rate':
            score = performance.get('win_rate', 0)
        elif selection_method == 'composite':
            # Composite score: weighted combination
            sharpe = performance.get('sharpe_ratio', 0)
            ret = performance.get('total_return', 0)
            win_rate = performance.get('win_rate', 0)
            dd = performance.get('max_drawdown', 1)
            
            # Normalize and combine
            score = (sharpe * 0.4 + ret * 0.3 + win_rate * 0.2 - dd * 0.1)
        else:
            score = 0
        
        strategy_scores[name] = score
    
    # Sort by score and return top N
    sorted_strategies = sorted(strategy_scores.items(), key=lambda x: x[1], reverse=True)
    selected = [name for name, score in sorted_strategies[:top_n]]
    
    return selected


def calculate_strategy_weights(strategy_results: Dict[str, Dict],
                              weighting_method: str = 'equal',
                              performance_window: int = 30) -> Dict[str, float]:
    """
    Calculate weights for each strategy in portfolio
    
    Args:
        strategy_results: Dictionary dengan strategy_name -> strategy_results
        weighting_method: Method untuk weighting ('equal', 'sharpe', 'inverse_vol', 'performance')
        performance_window: Window untuk performance calculation
    
    Returns:
        Dictionary dengan strategy_name -> weight
    """
    if weighting_method == 'equal':
        # Equal weighting
        n_strategies = len(strategy_results)
        return {name: 1.0 / n_strategies for name in strategy_results.keys()}
    
    elif weighting_method == 'sharpe':
        # Weight by Sharpe ratio
        sharpe_ratios = {}
        for name, results in strategy_results.items():
            if 'strategy_return' in results:
                returns = results['strategy_return']
                performance = calculate_strategy_performance(returns, performance_window)
                sharpe_ratios[name] = max(performance.get('sharpe_ratio', 0), 0)
        
        total_sharpe = sum(sharpe_ratios.values())
        if total_sharpe == 0:
            return {name: 1.0 / len(strategy_results) for name in strategy_results.keys()}
        
        return {name: sharpe / total_sharpe for name, sharpe in sharpe_ratios.items()}
    
    elif weighting_method == 'inverse_vol':
        # Weight by inverse volatility
        inv_vols = {}
        for name, results in strategy_results.items():
            if 'strategy_return' in results:
                returns = results['strategy_return']
                vol = returns.std() * np.sqrt(252)
                inv_vols[name] = 1.0 / vol if vol > 0 else 0
        
        total_inv_vol = sum(inv_vols.values())
        if total_inv_vol == 0:
            return {name: 1.0 / len(strategy_results) for name in strategy_results.keys()}
        
        return {name: inv_vol / total_inv_vol for name, inv_vol in inv_vols.items()}
    
    elif weighting_method == 'performance':
        # Weight by recent performance
        performances = {}
        for name, results in strategy_results.items():
            if 'strategy_return' in results:
                returns = results['strategy_return']
                performance = calculate_strategy_performance(returns, performance_window)
                performances[name] = max(performance.get('total_return', 0), 0)
        
        total_perf = sum(performances.values())
        if total_perf == 0:
            return {name: 1.0 / len(strategy_results) for name in strategy_results.keys()}
        
        return {name: perf / total_perf for name, perf in performances.items()}
    
    else:
        # Default: equal weighting
        n_strategies = len(strategy_results)
        return {name: 1.0 / n_strategies for name in strategy_results.keys()}


def combine_strategies(strategy_results: Dict[str, Dict],
                      weights: Optional[Dict[str, float]] = None,
                      selected_strategies: Optional[List[str]] = None) -> Dict:
    """
    Combine multiple strategies into portfolio
    
    Args:
        strategy_results: Dictionary dengan strategy_name -> strategy_results
        weights: Optional weights dictionary (if None, use equal weighting)
        selected_strategies: Optional list of strategies to include (if None, use all)
    
    Returns:
        Dictionary dengan combined strategy results
    """
    if selected_strategies is None:
        selected_strategies = list(strategy_results.keys())
    
    # Filter strategies
    filtered_results = {name: results for name, results in strategy_results.items() 
                       if name in selected_strategies and 'strategy_return' in results}
    
    if len(filtered_results) == 0:
        return {}
    
    # Get weights
    if weights is None:
        weights = {name: 1.0 / len(filtered_results) for name in filtered_results.keys()}
    
    # Align all return series
    all_returns = []
    for name, results in filtered_results.items():
        returns = results['strategy_return']
        all_returns.append(returns)
    
    # Align indices
    common_index = all_returns[0].index
    for returns in all_returns[1:]:
        common_index = common_index.intersection(returns.index)
    
    # Calculate weighted combination
    combined_returns = pd.Series(0.0, index=common_index)
    
    for name, results in filtered_results.items():
        returns = results['strategy_return']
        weight = weights.get(name, 0)
        aligned_returns = returns.loc[common_index]
        combined_returns += aligned_returns * weight
    
    # Calculate cumulative returns
    cumulative_return = (1 + combined_returns).cumprod()
    total_return = cumulative_return.iloc[-1] - 1 if len(cumulative_return) > 0 else 0
    
    return {
        'strategy_name': 'Multi-Strategy Portfolio',
        'strategies_used': selected_strategies,
        'weights': weights,
        'strategy_return': combined_returns,
        'cumulative_return': cumulative_return,
        'total_return': total_return,
        'num_strategies': len(selected_strategies)
    }


def print_portfolio_results(results: Dict):
    """Print portfolio results"""
    if not results:
        return
    
    print("\n" + "=" * 70)
    print("📊 MULTI-STRATEGY PORTFOLIO RESULTS")
    print("=" * 70)
    
    print(f"\n📈 Strategies Used: {', '.join(results.get('strategies_used', []))}")
    print(f"   Number of Strategies: {results.get('num_strategies', 0)}")
    
    if 'weights' in results:
        print(f"\n⚖️  Strategy Weights:")
        for name, weight in results['weights'].items():
            print(f"   {name}: {weight*100:.1f}%")
    
    total_return = results.get('total_return', 0)
    print(f"\n💰 Total Return: {total_return*100:.2f}%")
    
    if 'cumulative_return' in results:
        cum_ret = results['cumulative_return']
        if len(cum_ret) > 0:
            print(f"   Final Cumulative Return: {cum_ret.iloc[-1]:.4f}")
    
    print("\n" + "=" * 70)

