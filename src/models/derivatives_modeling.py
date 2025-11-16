"""
Derivatives Modeling Module
Implementasi Black-Scholes, Greeks, dan Options Strategies
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy.stats import norm
from scipy.optimize import minimize_scalar
import warnings
warnings.filterwarnings('ignore')


def black_scholes_price(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call') -> float:
    """
    Calculate Black-Scholes option price
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (in years)
        r: Risk-free rate
        sigma: Volatility (annualized)
        option_type: 'call' or 'put'
    
    Returns:
        Option price
    """
    if T <= 0:
        return max(S - K, 0) if option_type == 'call' else max(K - S, 0)
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type == 'call':
        price = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:  # put
        price = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    
    return price


def calculate_greeks(S: float, K: float, T: float, r: float, sigma: float, option_type: str = 'call') -> Dict:
    """
    Calculate option Greeks
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration (in years)
        r: Risk-free rate
        sigma: Volatility (annualized)
        option_type: 'call' or 'put'
    
    Returns:
        Dictionary dengan all Greeks
    """
    if T <= 0:
        return {
            'delta': 1.0 if (option_type == 'call' and S > K) or (option_type == 'put' and S < K) else 0.0,
            'gamma': 0.0,
            'theta': 0.0,
            'vega': 0.0,
            'rho': 0.0
        }
    
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    # Delta
    if option_type == 'call':
        delta = norm.cdf(d1)
    else:  # put
        delta = -norm.cdf(-d1)
    
    # Gamma (same for call and put)
    gamma = norm.pdf(d1) / (S * sigma * np.sqrt(T))
    
    # Theta
    if option_type == 'call':
        theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) - 
                r * K * np.exp(-r * T) * norm.cdf(d2)) / 365
    else:  # put
        theta = (-S * norm.pdf(d1) * sigma / (2 * np.sqrt(T)) + 
                r * K * np.exp(-r * T) * norm.cdf(-d2)) / 365
    
    # Vega (same for call and put)
    vega = S * norm.pdf(d1) * np.sqrt(T) / 100  # Divided by 100 for 1% change
    
    # Rho
    if option_type == 'call':
        rho = K * T * np.exp(-r * T) * norm.cdf(d2) / 100  # Divided by 100 for 1% change
    else:  # put
        rho = -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100
    
    return {
        'delta': delta,
        'gamma': gamma,
        'theta': theta,
        'vega': vega,
        'rho': rho
    }


def implied_volatility(market_price: float, S: float, K: float, T: float, r: float, option_type: str = 'call') -> float:
    """
    Calculate implied volatility from market price
    
    Args:
        market_price: Market price of option
        S: Current stock price
        K: Strike price
        T: Time to expiration (in years)
        r: Risk-free rate
        option_type: 'call' or 'put'
    
    Returns:
        Implied volatility
    """
    def objective(sigma):
        return abs(black_scholes_price(S, K, T, r, sigma, option_type) - market_price)
    
    result = minimize_scalar(objective, bounds=(0.001, 5.0), method='bounded')
    return result.x


def covered_call_strategy(S: float, K: float, T: float, r: float, sigma: float, 
                         shares: int = 100) -> Dict:
    """
    Covered Call Strategy: Long stock + Short call
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration
        r: Risk-free rate
        sigma: Volatility
        shares: Number of shares
    
    Returns:
        Dictionary dengan strategy details
    """
    call_price = black_scholes_price(S, K, T, r, sigma, 'call')
    call_greeks = calculate_greeks(S, K, T, r, sigma, 'call')
    
    # Strategy: Long stock, Short call
    strategy_delta = shares - shares * call_greeks['delta']
    strategy_gamma = -shares * call_greeks['gamma']
    strategy_theta = -shares * call_greeks['theta']
    strategy_vega = -shares * call_greeks['vega']
    
    # Profit at expiration for different stock prices
    stock_prices = np.linspace(S * 0.5, S * 1.5, 100)
    profits = []
    
    for stock_price in stock_prices:
        stock_profit = (stock_price - S) * shares
        call_profit = -max(stock_price - K, 0) * shares + call_price * shares
        total_profit = stock_profit + call_profit
        profits.append(total_profit)
    
    return {
        'strategy_name': 'Covered Call',
        'stock_position': shares,
        'call_position': -shares,
        'call_price': call_price,
        'premium_received': call_price * shares,
        'breakeven': S - call_price,
        'max_profit': (K - S + call_price) * shares,
        'max_loss': -S * shares,  # If stock goes to 0
        'delta': strategy_delta,
        'gamma': strategy_gamma,
        'theta': strategy_theta,
        'vega': strategy_vega,
        'profit_curve': {
            'stock_prices': stock_prices.tolist(),
            'profits': profits
        }
    }


def protective_put_strategy(S: float, K: float, T: float, r: float, sigma: float,
                            shares: int = 100) -> Dict:
    """
    Protective Put Strategy: Long stock + Long put
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration
        r: Risk-free rate
        sigma: Volatility
        shares: Number of shares
    
    Returns:
        Dictionary dengan strategy details
    """
    put_price = black_scholes_price(S, K, T, r, sigma, 'put')
    put_greeks = calculate_greeks(S, K, T, r, sigma, 'put')
    
    # Strategy: Long stock, Long put
    strategy_delta = shares + shares * put_greeks['delta']
    strategy_gamma = shares * put_greeks['gamma']
    strategy_theta = shares * put_greeks['theta']
    strategy_vega = shares * put_greeks['vega']
    
    # Profit at expiration
    stock_prices = np.linspace(S * 0.5, S * 1.5, 100)
    profits = []
    
    for stock_price in stock_prices:
        stock_profit = (stock_price - S) * shares
        put_profit = max(K - stock_price, 0) * shares - put_price * shares
        total_profit = stock_profit + put_profit
        profits.append(total_profit)
    
    return {
        'strategy_name': 'Protective Put',
        'stock_position': shares,
        'put_position': shares,
        'put_price': put_price,
        'premium_paid': put_price * shares,
        'breakeven': S + put_price,
        'max_profit': np.inf,  # Unlimited upside
        'max_loss': (S - K + put_price) * shares,  # If stock goes below strike
        'delta': strategy_delta,
        'gamma': strategy_gamma,
        'theta': strategy_theta,
        'vega': strategy_vega,
        'profit_curve': {
            'stock_prices': stock_prices.tolist(),
            'profits': profits
        }
    }


def straddle_strategy(S: float, K: float, T: float, r: float, sigma: float,
                     contracts: int = 1) -> Dict:
    """
    Straddle Strategy: Long call + Long put (same strike)
    
    Args:
        S: Current stock price
        K: Strike price
        T: Time to expiration
        r: Risk-free rate
        sigma: Volatility
        contracts: Number of contracts (each contract = 100 shares)
    
    Returns:
        Dictionary dengan strategy details
    """
    shares = contracts * 100
    
    call_price = black_scholes_price(S, K, T, r, sigma, 'call')
    put_price = black_scholes_price(S, K, T, r, sigma, 'put')
    
    call_greeks = calculate_greeks(S, K, T, r, sigma, 'call')
    put_greeks = calculate_greeks(S, K, T, r, sigma, 'put')
    
    total_cost = (call_price + put_price) * shares
    
    # Strategy Greeks
    strategy_delta = shares * (call_greeks['delta'] + put_greeks['delta'])
    strategy_gamma = shares * (call_greeks['gamma'] + put_greeks['gamma'])
    strategy_theta = shares * (call_greeks['theta'] + put_greeks['theta'])
    strategy_vega = shares * (call_greeks['vega'] + put_greeks['vega'])
    
    # Profit at expiration
    stock_prices = np.linspace(S * 0.7, S * 1.3, 100)
    profits = []
    
    for stock_price in stock_prices:
        call_profit = max(stock_price - K, 0) * shares - call_price * shares
        put_profit = max(K - stock_price, 0) * shares - put_price * shares
        total_profit = call_profit + put_profit
        profits.append(total_profit)
    
    # Breakeven points
    breakeven_up = K + (call_price + put_price)
    breakeven_down = K - (call_price + put_price)
    
    return {
        'strategy_name': 'Straddle',
        'call_position': shares,
        'put_position': shares,
        'total_cost': total_cost,
        'breakeven_up': breakeven_up,
        'breakeven_down': breakeven_down,
        'max_profit': np.inf,  # Unlimited if stock moves far enough
        'max_loss': -total_cost,  # If stock stays at strike
        'delta': strategy_delta,
        'gamma': strategy_gamma,
        'theta': strategy_theta,
        'vega': strategy_vega,
        'profit_curve': {
            'stock_prices': stock_prices.tolist(),
            'profits': profits
        }
    }


def print_derivatives_results(results: Dict):
    """Print derivatives strategy results"""
    if not results:
        return
    
    strategy_name = results.get('strategy_name', 'Unknown')
    
    print("\n" + "=" * 70)
    print(f"📊 {strategy_name.upper()} STRATEGY")
    print("=" * 70)
    
    if 'call_price' in results:
        print(f"\n💰 Call Price: ${results['call_price']:.2f}")
    if 'put_price' in results:
        print(f"💰 Put Price: ${results['put_price']:.2f}")
    if 'total_cost' in results:
        print(f"💰 Total Cost: ${results['total_cost']:.2f}")
    
    print(f"\n📈 Greeks:")
    print(f"   Delta: {results.get('delta', 0):.4f}")
    print(f"   Gamma: {results.get('gamma', 0):.6f}")
    print(f"   Theta: {results.get('theta', 0):.4f} (per day)")
    print(f"   Vega: {results.get('vega', 0):.4f} (per 1% vol change)")
    print(f"   Rho: {results.get('rho', 0):.4f} (per 1% rate change)")
    
    if 'breakeven' in results:
        print(f"\n🎯 Breakeven: ${results['breakeven']:.2f}")
    if 'breakeven_up' in results:
        print(f"🎯 Breakeven (Up): ${results['breakeven_up']:.2f}")
        print(f"🎯 Breakeven (Down): ${results['breakeven_down']:.2f}")
    
    if 'max_profit' in results:
        max_profit = results['max_profit']
        if np.isinf(max_profit):
            print(f"📈 Max Profit: Unlimited")
        else:
            print(f"📈 Max Profit: ${max_profit:.2f}")
    
    if 'max_loss' in results:
        print(f"📉 Max Loss: ${results['max_loss']:.2f}")
    
    print("\n" + "=" * 70)

