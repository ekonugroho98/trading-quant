"""
Hyperparameter Optimization Module
Grid Search, Random Search, dan Bayesian Optimization
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from sklearn.model_selection import TimeSeriesSplit
import warnings
warnings.filterwarnings('ignore')


def time_series_cv_split(data: pd.DataFrame, 
                        n_splits: int = 5,
                        test_size: Optional[int] = None) -> List[Tuple[np.ndarray, np.ndarray]]:
    """
    Time Series Cross-Validation Split
    
    Args:
        data: DataFrame dengan data
        n_splits: Number of splits
        test_size: Size of test set (default: len(data) // (n_splits + 1))
    
    Returns:
        List of (train_idx, test_idx) tuples
    """
    from sklearn.model_selection import TimeSeriesSplit
    
    if test_size is None:
        test_size = len(data) // (n_splits + 1)
    
    tscv = TimeSeriesSplit(n_splits=n_splits, test_size=test_size)
    splits = []
    
    for train_idx, test_idx in tscv.split(data):
        splits.append((train_idx, test_idx))
    
    return splits


def purged_cv_split(data: pd.DataFrame,
                    n_splits: int = 5,
                    test_size: Optional[int] = None,
                    purge_gap: int = 10) -> List[Tuple[np.ndarray, np.ndarray]]:
    """
    Purged Cross-Validation dengan gap antara train dan test
    
    Args:
        data: DataFrame dengan data
        n_splits: Number of splits
        test_size: Size of test set
        purge_gap: Gap antara train dan test (untuk menghindari look-ahead bias)
    
    Returns:
        List of (train_idx, test_idx) tuples
    """
    if test_size is None:
        test_size = len(data) // (n_splits + 1)
    
    splits = []
    total_size = len(data)
    
    for i in range(n_splits):
        # Test set
        test_start = total_size - (n_splits - i) * test_size
        test_end = test_start + test_size
        
        # Train set (sebelum test_start dengan gap)
        train_end = test_start - purge_gap
        train_start = max(0, train_end - (total_size // n_splits))
        
        if train_start < train_end and test_start < test_end and test_end <= total_size:
            train_idx = np.arange(train_start, train_end)
            test_idx = np.arange(test_start, test_end)
            splits.append((train_idx, test_idx))
    
    return splits


def grid_search_optimization(model_class,
                             param_grid: Dict[str, List],
                             X: np.ndarray,
                             y: np.ndarray,
                             cv_splits: List[Tuple[np.ndarray, np.ndarray]],
                             scoring: str = 'accuracy',
                             n_jobs: int = -1) -> Dict:
    """
    Grid Search untuk hyperparameter optimization
    
    Args:
        model_class: Model class (e.g., RandomForestClassifier)
        param_grid: Dictionary dengan parameter grid
        X: Feature matrix
        y: Target vector
        cv_splits: Cross-validation splits
        scoring: Scoring metric
        n_jobs: Number of parallel jobs
    
    Returns:
        Dictionary dengan best parameters dan score
    """
    from sklearn.model_selection import GridSearchCV
    from sklearn.metrics import make_scorer, accuracy_score
    
    # Create custom CV iterator
    class TimeSeriesCV:
        def __init__(self, splits):
            self.splits = splits
        
        def split(self, X, y=None, groups=None):
            for train_idx, test_idx in self.splits:
                yield train_idx, test_idx
        
        def get_n_splits(self, X=None, y=None, groups=None):
            return len(self.splits)
    
    cv = TimeSeriesCV(cv_splits)
    
    # Create model
    model = model_class()
    
    # Grid search
    grid_search = GridSearchCV(
        model,
        param_grid,
        cv=cv,
        scoring=scoring,
        n_jobs=n_jobs,
        verbose=0
    )
    
    grid_search.fit(X, y)
    
    return {
        'best_params': grid_search.best_params_,
        'best_score': grid_search.best_score_,
        'best_model': grid_search.best_estimator_,
        'cv_results': grid_search.cv_results_
    }


def random_search_optimization(model_class,
                               param_distributions: Dict[str, List],
                               X: np.ndarray,
                               y: np.ndarray,
                               cv_splits: List[Tuple[np.ndarray, np.ndarray]],
                               n_iter: int = 50,
                               scoring: str = 'accuracy',
                               n_jobs: int = -1,
                               random_state: int = 42) -> Dict:
    """
    Random Search untuk hyperparameter optimization
    
    Args:
        model_class: Model class
        param_distributions: Dictionary dengan parameter distributions
        X: Feature matrix
        y: Target vector
        cv_splits: Cross-validation splits
        n_iter: Number of iterations
        scoring: Scoring metric
        n_jobs: Number of parallel jobs
        random_state: Random seed
    
    Returns:
        Dictionary dengan best parameters dan score
    """
    from sklearn.model_selection import RandomizedSearchCV
    
    # Create custom CV iterator
    class TimeSeriesCV:
        def __init__(self, splits):
            self.splits = splits
        
        def split(self, X, y=None, groups=None):
            for train_idx, test_idx in self.splits:
                yield train_idx, test_idx
        
        def get_n_splits(self, X=None, y=None, groups=None):
            return len(self.splits)
    
    cv = TimeSeriesCV(cv_splits)
    
    # Create model
    model = model_class()
    
    # Random search
    random_search = RandomizedSearchCV(
        model,
        param_distributions,
        n_iter=n_iter,
        cv=cv,
        scoring=scoring,
        n_jobs=n_jobs,
        random_state=random_state,
        verbose=0
    )
    
    random_search.fit(X, y)
    
    return {
        'best_params': random_search.best_params_,
        'best_score': random_search.best_score_,
        'best_model': random_search.best_estimator_,
        'cv_results': random_search.cv_results_
    }


def bayesian_optimization(model_class,
                          param_space: List,
                          X: np.ndarray,
                          y: np.ndarray,
                          cv_splits: List[Tuple[np.ndarray, np.ndarray]],
                          n_calls: int = 50,
                          scoring: str = 'accuracy',
                          random_state: int = 42) -> Dict:
    """
    Bayesian Optimization menggunakan scikit-optimize
    
    Args:
        model_class: Model class
        param_space: List of skopt.space objects
        X: Feature matrix
        y: Target vector
        cv_splits: Cross-validation splits
        n_calls: Number of optimization iterations
        scoring: Scoring metric
        random_state: Random seed
    
    Returns:
        Dictionary dengan best parameters dan score
    """
    try:
        from skopt import gp_minimize
        from skopt.space import Real, Integer, Categorical
        from sklearn.metrics import make_scorer, accuracy_score
    except ImportError:
        raise ImportError("scikit-optimize tidak tersedia. Install dengan: pip install scikit-optimize")
    
    # Objective function
    def objective(params):
        # Convert params to dict
        param_dict = {}
        for i, space in enumerate(param_space):
            param_dict[space.name] = params[i]
        
        # Create model dengan parameters
        model = model_class(**param_dict)
        
        # Cross-validation
        scores = []
        for train_idx, test_idx in cv_splits:
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)
            
            if scoring == 'accuracy':
                score = accuracy_score(y_test, y_pred)
            else:
                # Default to accuracy
                score = accuracy_score(y_test, y_pred)
            
            scores.append(score)
        
        # Return negative score (minimize)
        return -np.mean(scores)
    
    # Run optimization
    result = gp_minimize(
        objective,
        param_space,
        n_calls=n_calls,
        random_state=random_state,
        verbose=False
    )
    
    # Convert best params to dict
    best_params = {}
    for i, space in enumerate(param_space):
        best_params[space.name] = result.x[i]
    
    return {
        'best_params': best_params,
        'best_score': -result.fun,  # Negative karena kita minimize
        'optimization_result': result
    }


def optimize_random_forest(X: np.ndarray,
                           y: np.ndarray,
                           is_classification: bool = True,
                           method: str = 'random_search',
                           cv_splits: Optional[List] = None,
                           n_splits: int = 5) -> Dict:
    """
    Optimize Random Forest hyperparameters
    
    Args:
        X: Feature matrix
        y: Target vector
        is_classification: True untuk classification, False untuk regression
        method: 'grid_search', 'random_search', atau 'bayesian'
        cv_splits: Optional pre-computed CV splits
        n_splits: Number of CV splits jika cv_splits tidak provided
    
    Returns:
        Dictionary dengan best parameters
    """
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    
    if is_classification:
        model_class = RandomForestClassifier
        param_grid = {
            'n_estimators': [100, 200, 300],
            'max_depth': [5, 10, 15, None],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4],
            'max_features': ['sqrt', 'log2', None]
        }
    else:
        model_class = RandomForestRegressor
        param_grid = {
            'n_estimators': [100, 200, 300],
            'max_depth': [5, 10, 15, None],
            'min_samples_split': [2, 5, 10],
            'min_samples_leaf': [1, 2, 4],
            'max_features': ['sqrt', 'log2', None]
        }
    
    # Create CV splits jika tidak provided
    if cv_splits is None:
        data_df = pd.DataFrame(X)
        cv_splits = time_series_cv_split(data_df, n_splits=n_splits)
    
    if method == 'grid_search':
        return grid_search_optimization(model_class, param_grid, X, y, cv_splits)
    elif method == 'random_search':
        return random_search_optimization(model_class, param_grid, X, y, cv_splits, n_iter=50)
    elif method == 'bayesian':
        try:
            from skopt.space import Integer, Categorical
            param_space = [
                Integer(50, 300, name='n_estimators'),
                Integer(3, 20, name='max_depth'),
                Integer(2, 10, name='min_samples_split'),
                Integer(1, 5, name='min_samples_leaf'),
                Categorical(['sqrt', 'log2', None], name='max_features')
            ]
            return bayesian_optimization(model_class, param_space, X, y, cv_splits, n_calls=50)
        except ImportError:
            print("⚠️  scikit-optimize tidak tersedia, menggunakan random_search")
            return random_search_optimization(model_class, param_grid, X, y, cv_splits, n_iter=50)
    else:
        raise ValueError(f"Method {method} tidak dikenal. Gunakan 'grid_search', 'random_search', atau 'bayesian'")


def optimize_xgboost(X: np.ndarray,
                     y: np.ndarray,
                     is_classification: bool = True,
                     method: str = 'random_search',
                     cv_splits: Optional[List] = None,
                     n_splits: int = 5) -> Dict:
    """
    Optimize XGBoost hyperparameters
    
    Args:
        X: Feature matrix
        y: Target vector
        is_classification: True untuk classification, False untuk regression
        method: 'grid_search', 'random_search', atau 'bayesian'
        cv_splits: Optional pre-computed CV splits
        n_splits: Number of CV splits jika cv_splits tidak provided
    
    Returns:
        Dictionary dengan best parameters
    """
    try:
        from xgboost import XGBClassifier, XGBRegressor
    except ImportError:
        raise ImportError("XGBoost tidak tersedia. Install dengan: pip install xgboost")
    
    if is_classification:
        model_class = XGBClassifier
    else:
        model_class = XGBRegressor
    
    param_grid = {
        'n_estimators': [100, 200, 300],
        'max_depth': [3, 6, 9],
        'learning_rate': [0.01, 0.1, 0.2],
        'subsample': [0.6, 0.8, 1.0],
        'colsample_bytree': [0.6, 0.8, 1.0]
    }
    
    # Create CV splits jika tidak provided
    if cv_splits is None:
        data_df = pd.DataFrame(X)
        cv_splits = time_series_cv_split(data_df, n_splits=n_splits)
    
    if method == 'random_search':
        return random_search_optimization(model_class, param_grid, X, y, cv_splits, n_iter=50)
    elif method == 'bayesian':
        try:
            from skopt.space import Integer, Real
            param_space = [
                Integer(50, 300, name='n_estimators'),
                Integer(3, 10, name='max_depth'),
                Real(0.01, 0.3, name='learning_rate'),
                Real(0.6, 1.0, name='subsample'),
                Real(0.6, 1.0, name='colsample_bytree')
            ]
            return bayesian_optimization(model_class, param_space, X, y, cv_splits, n_calls=50)
        except ImportError:
            print("⚠️  scikit-optimize tidak tersedia, menggunakan random_search")
            return random_search_optimization(model_class, param_grid, X, y, cv_splits, n_iter=50)
    else:
        return random_search_optimization(model_class, param_grid, X, y, cv_splits, n_iter=50)

