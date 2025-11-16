"""
Enhanced Backtesting Module
Implementasi Monte Carlo simulation dan Transaction Costs
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional


def calculate_transaction_costs(df: pd.DataFrame, 
                                commission_pct: float = 0.001,
                                slippage_pct: float = 0.0005) -> pd.DataFrame:
    """
    Calculate transaction costs (commission + slippage)
    
    Args:
        df: DataFrame dengan trading signals
        commission_pct: Commission percentage (default 0.1% = 0.001)
        slippage_pct: Slippage percentage (default 0.05% = 0.0005)
    
    Returns:
        DataFrame dengan kolom transaction costs
    """
    df = df.copy()
    
    # Detect trade entries (signal changes)
    df['Signal_Change'] = df['Signal'].diff().fillna(0)
    df['Trade_Entry'] = (df['Signal_Change'] != 0) & (df['Signal'] != 0)
    
    # Calculate transaction costs
    total_cost_pct = commission_pct + slippage_pct
    df['Transaction_Cost'] = 0.0
    df.loc[df['Trade_Entry'], 'Transaction_Cost'] = total_cost_pct
    
    # Adjust strategy returns with transaction costs
    if 'Strategy_Return' in df.columns:
        df['Strategy_Return_After_Costs'] = df['Strategy_Return'] - df['Transaction_Cost']
        df['Cumulative_Strategy_After_Costs'] = (1 + df['Strategy_Return_After_Costs']).cumprod()
    
    return df


def monte_carlo_simulation(returns: pd.Series, 
                          num_simulations: int = 1000,
                          num_periods: int = None) -> Dict:
    """
    Run Monte Carlo simulation on returns
    
    Args:
        returns: Series dengan historical returns
        num_simulations: Number of simulations to run
        num_periods: Number of periods to simulate (default = len(returns))
    
    Returns:
        Dictionary dengan simulation results
    """
    if num_periods is None:
        num_periods = len(returns)
    
    # Remove NaN values
    returns_clean = returns.dropna()
    
    if len(returns_clean) == 0:
        return {}
    
    # Calculate statistics
    mean_return = returns_clean.mean()
    std_return = returns_clean.std()
    
    # Run simulations
    simulations = []
    final_returns = []
    
    for _ in range(num_simulations):
        # Generate random returns based on historical distribution
        sim_returns = np.random.normal(mean_return, std_return, num_periods)
        
        # Calculate cumulative return
        cum_return = (1 + pd.Series(sim_returns)).cumprod()
        simulations.append(cum_return)
        final_returns.append(cum_return.iloc[-1])
    
    # Convert to DataFrame
    simulations_df = pd.DataFrame(simulations).T
    
    # Calculate statistics
    final_returns = np.array(final_returns)
    
    return {
        'simulations': simulations_df,
        'mean_final_return': final_returns.mean(),
        'median_final_return': np.median(final_returns),
        'std_final_return': final_returns.std(),
        'percentile_5': np.percentile(final_returns, 5),
        'percentile_25': np.percentile(final_returns, 25),
        'percentile_75': np.percentile(final_returns, 75),
        'percentile_95': np.percentile(final_returns, 95),
        'probability_profit': (final_returns > 1.0).sum() / len(final_returns),
        'probability_loss': (final_returns < 1.0).sum() / len(final_returns)
    }


def calculate_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """
    Calculate Sharpe Ratio
    
    Args:
        returns: Series dengan returns
        risk_free_rate: Risk-free rate (default 0.0)
    
    Returns:
        Sharpe ratio
    """
    returns_clean = returns.dropna()
    
    if len(returns_clean) == 0 or returns_clean.std() == 0:
        return 0.0
    
    excess_returns = returns_clean - risk_free_rate
    sharpe = excess_returns.mean() / returns_clean.std()
    
    # Annualize (assuming daily returns)
    sharpe_annualized = sharpe * np.sqrt(252)
    
    return sharpe_annualized


def calculate_sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """
    Calculate Sortino Ratio (uses downside deviation instead of total volatility)
    
    Args:
        returns: Series dengan returns
        risk_free_rate: Risk-free rate (default 0.0)
    
    Returns:
        Sortino ratio
    """
    returns_clean = returns.dropna()
    
    if len(returns_clean) == 0:
        return 0.0
    
    excess_returns = returns_clean - risk_free_rate
    
    # Calculate downside deviation (only negative returns)
    downside_returns = returns_clean[returns_clean < 0]
    
    if len(downside_returns) == 0 or downside_returns.std() == 0:
        return 0.0
    
    downside_std = downside_returns.std()
    sortino = excess_returns.mean() / downside_std
    
    # Annualize (assuming daily returns)
    sortino_annualized = sortino * np.sqrt(252)
    
    return sortino_annualized


def calculate_calmar_ratio(returns: pd.Series, max_drawdown: float) -> float:
    """
    Calculate Calmar Ratio (return / max drawdown)
    
    Args:
        returns: Series dengan returns
        max_drawdown: Maximum drawdown (as positive number)
    
    Returns:
        Calmar ratio
    """
    returns_clean = returns.dropna()
    
    if len(returns_clean) == 0 or max_drawdown == 0:
        return 0.0
    
    # Annualized return
    total_return = (1 + returns_clean).prod() - 1
    num_years = len(returns_clean) / 252  # Assuming daily data
    
    if num_years == 0:
        return 0.0
    
    annualized_return = (1 + total_return) ** (1 / num_years) - 1
    
    # Calmar ratio
    calmar = annualized_return / max_drawdown
    
    return calmar


def run_enhanced_backtest(df: pd.DataFrame,
                         commission_pct: float = 0.001,
                         slippage_pct: float = 0.0005,
                         num_simulations: int = 1000) -> Dict:
    """
    Run enhanced backtest with transaction costs and Monte Carlo
    
    Args:
        df: DataFrame dengan strategy data
        commission_pct: Commission percentage
        slippage_pct: Slippage percentage
        num_simulations: Number of Monte Carlo simulations
    
    Returns:
        Dictionary dengan backtest results
    """
    results = {}
    
    # Calculate transaction costs
    df_with_costs = calculate_transaction_costs(df, commission_pct, slippage_pct)
    
    # Calculate returns before and after costs
    if 'Strategy_Return' in df.columns:
        returns_before = df['Strategy_Return'].dropna()
        returns_after = df_with_costs['Strategy_Return_After_Costs'].dropna()
        
        # Total returns
        total_return_before = (1 + returns_before).prod() - 1
        total_return_after = (1 + returns_after).prod() - 1
        
        results['total_return_before_costs'] = total_return_before
        results['total_return_after_costs'] = total_return_after
        results['cost_impact'] = total_return_before - total_return_after
        results['cost_impact_pct'] = (results['cost_impact'] / total_return_before * 100) if total_return_before != 0 else 0
        
        # Sharpe and Sortino ratios
        results['sharpe_ratio_before'] = calculate_sharpe_ratio(returns_before)
        results['sharpe_ratio_after'] = calculate_sharpe_ratio(returns_after)
        results['sortino_ratio_before'] = calculate_sortino_ratio(returns_before)
        results['sortino_ratio_after'] = calculate_sortino_ratio(returns_after)
        
        # Monte Carlo simulation
        mc_results = monte_carlo_simulation(returns_after, num_simulations)
        results['monte_carlo'] = mc_results
    
    results['df_with_costs'] = df_with_costs
    
    return results


def print_backtest_results(results: Dict):
    """Print enhanced backtest results"""
    if not results:
        return
    
    print("\n" + "=" * 70)
    print("🔬 ENHANCED BACKTESTING RESULTS")
    print("=" * 70)
    
    # Transaction costs impact
    print(f"\n💰 Transaction Costs Impact:")
    print(f"   Return Before Costs: {results.get('total_return_before_costs', 0)*100:.2f}%")
    print(f"   Return After Costs: {results.get('total_return_after_costs', 0)*100:.2f}%")
    print(f"   Cost Impact: {results.get('cost_impact', 0)*100:.2f}% ({results.get('cost_impact_pct', 0):.1f}% of returns)")
    
    # Risk-adjusted returns
    print(f"\n📊 Risk-Adjusted Returns:")
    print(f"   Sharpe Ratio (Before): {results.get('sharpe_ratio_before', 0):.2f}")
    print(f"   Sharpe Ratio (After): {results.get('sharpe_ratio_after', 0):.2f}")
    print(f"   Sortino Ratio (Before): {results.get('sortino_ratio_before', 0):.2f}")
    print(f"   Sortino Ratio (After): {results.get('sortino_ratio_after', 0):.2f}")
    
    # Monte Carlo results
    if 'monte_carlo' in results:
        mc = results['monte_carlo']
        print(f"\n🎲 Monte Carlo Simulation ({len(mc.get('simulations', [])) if 'simulations' in mc else 0} runs):")
        print(f"   Mean Final Return: {(mc.get('mean_final_return', 1)-1)*100:.2f}%")
        print(f"   Median Final Return: {(mc.get('median_final_return', 1)-1)*100:.2f}%")
        print(f"   5th Percentile: {(mc.get('percentile_5', 1)-1)*100:.2f}%")
        print(f"   95th Percentile: {(mc.get('percentile_95', 1)-1)*100:.2f}%")
        print(f"   Probability of Profit: {mc.get('probability_profit', 0)*100:.1f}%")
        print(f"   Probability of Loss: {mc.get('probability_loss', 0)*100:.1f}%")
    
    print("\n" + "=" * 70)
