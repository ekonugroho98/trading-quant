"""
Parameter Optimization Module
Grid search, walk-forward optimization, dan genetic algorithm untuk strategy parameters
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Callable, Any
from itertools import product
import logging
from dataclasses import dataclass

logger = logging.getLogger('parameter_optimization')


@dataclass
class OptimizationResult:
    """Result dari parameter optimization"""
    best_params: Dict[str, Any]
    best_score: float
    all_results: List[Dict[str, Any]]
    optimization_method: str


def grid_search(parameter_grid: Dict[str, List[Any]],
                objective_function: Callable[[Dict[str, Any]], float],
                maximize: bool = True) -> OptimizationResult:
    """
    Grid search untuk parameter optimization
    
    Args:
        parameter_grid: Dictionary dengan parameter names dan possible values
        objective_function: Function yang menerima parameters dan return score
        maximize: True untuk maximize score, False untuk minimize
    
    Returns:
        OptimizationResult dengan best parameters
    """
    logger.info(f"Starting grid search with {len(parameter_grid)} parameters")
    
    # Generate all parameter combinations
    param_names = list(parameter_grid.keys())
    param_values = list(parameter_grid.values())
    all_combinations = list(product(*param_values))
    
    logger.info(f"Testing {len(all_combinations)} parameter combinations")
    
    results = []
    best_score = float('-inf') if maximize else float('inf')
    best_params = None
    
    for i, combination in enumerate(all_combinations):
        params = dict(zip(param_names, combination))
        
        try:
            score = objective_function(params)
            results.append({
                'params': params,
                'score': score
            })
            
            if (maximize and score > best_score) or (not maximize and score < best_score):
                best_score = score
                best_params = params
            
            if (i + 1) % 10 == 0:
                logger.info(f"Progress: {i + 1}/{len(all_combinations)} combinations tested")
        
        except Exception as e:
            logger.warning(f"Error evaluating parameters {params}: {e}")
            continue
    
    logger.info(f"Grid search completed. Best score: {best_score:.4f}")
    
    return OptimizationResult(
        best_params=best_params,
        best_score=best_score,
        all_results=results,
        optimization_method='grid_search'
    )


def walk_forward_optimization(data: pd.DataFrame,
                             train_window: int,
                             test_window: int,
                             step_size: int,
                             parameter_grid: Dict[str, List[Any]],
                             objective_function: Callable[[pd.DataFrame, Dict[str, Any]], float],
                             maximize: bool = True) -> OptimizationResult:
    """
    Walk-forward optimization untuk parameter tuning
    
    Args:
        data: Historical data
        train_window: Training window size
        test_window: Testing window size
        step_size: Step size for rolling window
        parameter_grid: Parameter grid untuk optimization
        objective_function: Function yang menerima data dan parameters, return score
        maximize: True untuk maximize score, False untuk minimize
    
    Returns:
        OptimizationResult dengan best parameters
    """
    logger.info(f"Starting walk-forward optimization")
    logger.info(f"Train window: {train_window}, Test window: {test_window}, Step: {step_size}")
    
    all_results = []
    window_scores = []
    
    # Run grid search untuk each training window
    for start_idx in range(0, len(data) - train_window - test_window, step_size):
        train_end = start_idx + train_window
        test_start = train_end
        test_end = test_start + test_window
        
        if test_end > len(data):
            break
        
        train_data = data.iloc[start_idx:train_end]
        test_data = data.iloc[test_start:test_end]
        
        logger.info(f"Window {len(window_scores) + 1}: Train [{start_idx}:{train_end}], Test [{test_start}:{test_end}]")
        
        # Objective function untuk this window
        def window_objective(params: Dict[str, Any]) -> float:
            # Train on training data
            train_score = objective_function(train_data, params)
            return train_score
        
        # Grid search untuk this window
        window_result = grid_search(parameter_grid, window_objective, maximize)
        
        # Test on test data
        test_score = objective_function(test_data, window_result.best_params)
        
        window_scores.append(test_score)
        all_results.append({
            'window': len(window_scores),
            'train_start': start_idx,
            'train_end': train_end,
            'test_start': test_start,
            'test_end': test_end,
            'best_params': window_result.best_params,
            'train_score': window_result.best_score,
            'test_score': test_score
        })
    
    # Find best parameters based on average test score
    if window_scores:
        avg_scores = {}
        for result in all_results:
            params_key = str(sorted(result['best_params'].items()))
            if params_key not in avg_scores:
                avg_scores[params_key] = []
            avg_scores[params_key].append(result['test_score'])
        
        # Calculate average score for each parameter set
        param_avg_scores = {
            params_key: np.mean(scores) for params_key, scores in avg_scores.items()
        }
        
        # Find best
        if maximize:
            best_key = max(param_avg_scores, key=param_avg_scores.get)
        else:
            best_key = min(param_avg_scores, key=param_avg_scores.get)
        
        # Extract best parameters
        best_params = eval(best_key) if isinstance(best_key, str) else best_key
        best_params = dict(best_params)
        best_score = param_avg_scores[best_key]
        
        logger.info(f"Walk-forward optimization completed. Best avg test score: {best_score:.4f}")
        
        return OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            all_results=all_results,
            optimization_method='walk_forward'
        )
    else:
        logger.warning("No windows processed in walk-forward optimization")
        return OptimizationResult(
            best_params=None,
            best_score=0.0,
            all_results=[],
            optimization_method='walk_forward'
        )


def optimize_strategy_parameters(data: pd.DataFrame,
                                strategy_function: Callable,
                                parameter_grid: Dict[str, List[Any]],
                                optimization_method: str = 'grid_search',
                                objective_metric: str = 'sharpe_ratio',
                                train_window: Optional[int] = None,
                                test_window: Optional[int] = None) -> OptimizationResult:
    """
    Optimize strategy parameters
    
    Args:
        data: Historical data
        strategy_function: Strategy function yang menerima data dan parameters
        parameter_grid: Parameter grid
        optimization_method: 'grid_search' atau 'walk_forward'
        objective_metric: Metric untuk optimization ('sharpe_ratio', 'total_return', 'win_rate')
        train_window: Training window untuk walk-forward
        test_window: Testing window untuk walk-forward
    
    Returns:
        OptimizationResult
    """
    logger.info(f"Optimizing strategy parameters using {optimization_method}")
    
    # Define objective function
    def calculate_metric(strategy_result: Dict[str, Any], metric: str) -> float:
        """Calculate metric from strategy result"""
        if metric == 'sharpe_ratio':
            returns = strategy_result.get('strategy_return', pd.Series())
            if len(returns) == 0 or returns.std() == 0:
                return 0.0
            return returns.mean() / returns.std() * np.sqrt(252)
        
        elif metric == 'total_return':
            return strategy_result.get('total_return', 0.0)
        
        elif metric == 'win_rate':
            signals = strategy_result.get('signals', pd.Series())
            returns = strategy_result.get('strategy_return', pd.Series())
            if len(returns) == 0:
                return 0.0
            win_rate = (returns > 0).sum() / len(returns)
            return win_rate
        
        else:
            logger.warning(f"Unknown metric: {metric}")
            return 0.0
    
    def objective_function(params: Dict[str, Any]) -> float:
        """Objective function untuk optimization"""
        try:
            result = strategy_function(data, **params)
            score = calculate_metric(result, objective_metric)
            return score
        except Exception as e:
            logger.warning(f"Error in objective function with params {params}: {e}")
            return float('-inf')
    
    if optimization_method == 'grid_search':
        return grid_search(parameter_grid, objective_function, maximize=True)
    
    elif optimization_method == 'walk_forward':
        if train_window is None or test_window is None:
            raise ValueError("train_window and test_window required for walk-forward optimization")
        
        def walk_forward_objective(data_window: pd.DataFrame, params: Dict[str, Any]) -> float:
            """Objective function untuk walk-forward"""
            try:
                result = strategy_function(data_window, **params)
                return calculate_metric(result, objective_metric)
            except Exception as e:
                logger.warning(f"Error in walk-forward objective: {e}")
                return float('-inf')
        
        step_size = test_window  # Default step size
        return walk_forward_optimization(
            data, train_window, test_window, step_size,
            parameter_grid, walk_forward_objective, maximize=True
        )
    
    else:
        raise ValueError(f"Unknown optimization method: {optimization_method}")

