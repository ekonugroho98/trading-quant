"""
Ensemble Improvements Module
Dynamic model weighting, stacking, dan model diversity
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


def calculate_dynamic_weights(model_performances: List[float],
                             window: int = 30,
                             method: str = 'inverse_error') -> List[float]:
    """
    Calculate dynamic weights berdasarkan recent performance
    
    Args:
        model_performances: List of performance metrics untuk setiap model (recent N periods)
        window: Window size untuk recent performance
        method: 'inverse_error', 'exponential', atau 'linear'
    
    Returns:
        List of weights (normalized to sum to 1)
    """
    if len(model_performances) == 0:
        return []
    
    # Convert to numpy array
    performances = np.array(model_performances)
    
    if method == 'inverse_error':
        # Weight = inverse of error (higher performance = higher weight)
        # Convert accuracy to error
        errors = 1 - performances
        # Avoid division by zero
        errors = np.maximum(errors, 1e-6)
        weights = 1 / errors
    elif method == 'exponential':
        # Exponential weighting: weight = exp(performance)
        weights = np.exp(performances)
    elif method == 'linear':
        # Linear weighting: weight = performance
        weights = performances
    else:
        # Default: equal weights
        weights = np.ones(len(performances))
    
    # Normalize weights
    total_weight = np.sum(weights)
    if total_weight > 0:
        weights = weights / total_weight
    else:
        weights = np.ones(len(performances)) / len(performances)
    
    return weights.tolist()


def calculate_model_performance_history(predictions: List[np.ndarray],
                                       actuals: np.ndarray,
                                       metric: str = 'accuracy') -> List[float]:
    """
    Calculate performance history untuk setiap model
    
    Args:
        predictions: List of prediction arrays untuk setiap model
        actuals: Actual values
        metric: 'accuracy', 'mae', 'rmse', atau 'sharpe'
    
    Returns:
        List of performance metrics untuk setiap model
    """
    performances = []
    
    for pred in predictions:
        if metric == 'accuracy':
            # Classification accuracy
            correct = (pred == actuals).sum()
            perf = correct / len(actuals) if len(actuals) > 0 else 0
        elif metric == 'mae':
            # Mean Absolute Error
            perf = -np.mean(np.abs(pred - actuals))  # Negative karena kita ingin maximize
        elif metric == 'rmse':
            # Root Mean Squared Error
            perf = -np.sqrt(np.mean((pred - actuals) ** 2))  # Negative karena kita ingin maximize
        elif metric == 'sharpe':
            # Sharpe ratio dari returns
            returns = pred - actuals
            if returns.std() > 0:
                perf = returns.mean() / returns.std()
            else:
                perf = 0
        else:
            perf = 0
        
        performances.append(perf)
    
    return performances


def dynamic_weighted_ensemble(predictions: List[np.ndarray],
                             weights: List[float]) -> np.ndarray:
    """
    Combine predictions dengan dynamic weights
    
    Args:
        predictions: List of prediction arrays
        weights: List of weights untuk setiap model
    
    Returns:
        Weighted ensemble prediction
    """
    if len(predictions) != len(weights):
        raise ValueError("Number of predictions harus sama dengan number of weights")
    
    # Normalize weights
    weights = np.array(weights)
    weights = weights / weights.sum()
    
    # Weighted average
    ensemble_pred = np.zeros_like(predictions[0])
    for pred, weight in zip(predictions, weights):
        ensemble_pred += pred * weight
    
    return ensemble_pred


def stacking_ensemble(base_models: List,
                    meta_model,
                    X_train: np.ndarray,
                    y_train: np.ndarray,
                    X_val: Optional[np.ndarray] = None,
                    y_val: Optional[np.ndarray] = None,
                    use_cv: bool = True,
                    cv_splits: Optional[List] = None) -> Tuple[List, any]:
    """
    Stacking ensemble: train meta-model pada base model predictions
    
    Args:
        base_models: List of base models
        meta_model: Meta-learner model
        X_train: Training features
        y_train: Training targets
        X_val: Optional validation features
        y_val: Optional validation targets
        use_cv: Use cross-validation untuk base predictions
        cv_splits: Optional pre-computed CV splits
    
    Returns:
        Tuple of (trained_base_models, trained_meta_model)
    """
    from sklearn.model_selection import KFold
    
    if use_cv and cv_splits is None:
        # Create CV splits
        kf = KFold(n_splits=5, shuffle=False)
        cv_splits = list(kf.split(X_train))
    
    # Get base predictions menggunakan CV
    base_predictions = []
    
    if use_cv and cv_splits:
        # Out-of-fold predictions
        meta_X = np.zeros((len(X_train), len(base_models)))
        
        for i, model in enumerate(base_models):
            fold_predictions = np.zeros(len(X_train))
            
            for train_idx, val_idx in cv_splits:
                # Train model on fold
                model_copy = type(model)(**model.get_params()) if hasattr(model, 'get_params') else model
                model_copy.fit(X_train[train_idx], y_train[train_idx])
                
                # Predict on validation fold
                fold_predictions[val_idx] = model_copy.predict(X_train[val_idx])
            
            meta_X[:, i] = fold_predictions
            
            # Train final model on all data
            final_model = type(model)(**model.get_params()) if hasattr(model, 'get_params') else model
            final_model.fit(X_train, y_train)
            base_models[i] = final_model
    else:
        # Simple: train on train, predict on val
        if X_val is not None:
            meta_X = np.zeros((len(X_val), len(base_models)))
            
            for i, model in enumerate(base_models):
                model.fit(X_train, y_train)
                meta_X[:, i] = model.predict(X_val)
        else:
            # Use training data
            meta_X = np.zeros((len(X_train), len(base_models)))
            
            for i, model in enumerate(base_models):
                model.fit(X_train, y_train)
                meta_X[:, i] = model.predict(X_train)
    
    # Train meta-model
    if X_val is not None and y_val is not None:
        meta_model.fit(meta_X, y_val)
    else:
        meta_model.fit(meta_X, y_train)
    
    return base_models, meta_model


def predict_stacking_ensemble(base_models: List,
                              meta_model,
                              X: np.ndarray) -> np.ndarray:
    """
    Predict menggunakan stacking ensemble
    
    Args:
        base_models: List of trained base models
        meta_model: Trained meta-model
        X: Feature matrix
    
    Returns:
        Ensemble predictions
    """
    # Get base predictions
    base_predictions = np.zeros((len(X), len(base_models)))
    
    for i, model in enumerate(base_models):
        base_predictions[:, i] = model.predict(X)
    
    # Meta-model prediction
    ensemble_pred = meta_model.predict(base_predictions)
    
    return ensemble_pred


def prune_models_by_performance(models: List,
                               performances: List[float],
                               min_performance: float = 0.45) -> Tuple[List, List]:
    """
    Prune models dengan performance buruk
    
    Args:
        models: List of models
        performances: List of performance metrics
        min_performance: Minimum performance threshold
    
    Returns:
        Tuple of (pruned_models, pruned_performances)
    """
    pruned_models = []
    pruned_performances = []
    
    for model, perf in zip(models, performances):
        if perf >= min_performance:
            pruned_models.append(model)
            pruned_performances.append(perf)
    
    return pruned_models, pruned_performances


def ensure_model_diversity(models: List,
                          model_types: List[str]) -> List:
    """
    Ensure model diversity (tidak semua model sama jenisnya)
    
    Args:
        models: List of models
        model_types: List of model type names
    
    Returns:
        List of diverse models
    """
    if len(models) == 0:
        return []
    
    # Group models by type
    model_groups = {}
    for model, model_type in zip(models, model_types):
        if model_type not in model_groups:
            model_groups[model_type] = []
        model_groups[model_type].append(model)
    
    # Select at least one from each type
    diverse_models = []
    for model_type, type_models in model_groups.items():
        # Take best model dari setiap type (atau first jika tidak ada ranking)
        diverse_models.append(type_models[0])
    
    return diverse_models

