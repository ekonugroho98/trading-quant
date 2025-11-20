"""
Feature Selection Module
Feature importance analysis, RFE, dan correlation analysis
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


def calculate_feature_importance(model, feature_names: List[str]) -> pd.DataFrame:
    """
    Calculate feature importance dari model
    
    Args:
        model: Trained model dengan feature_importances_ attribute
        feature_names: List of feature names
    
    Returns:
        DataFrame dengan feature importance
    """
    if not hasattr(model, 'feature_importances_'):
        return pd.DataFrame()
    
    importance_df = pd.DataFrame({
        'feature': feature_names,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    return importance_df


def recursive_feature_elimination(X: pd.DataFrame,
                                  y: pd.Series,
                                  model_class,
                                  n_features_to_select: int,
                                  cv_splits: Optional[List] = None,
                                  n_splits: int = 5) -> List[str]:
    """
    Recursive Feature Elimination
    
    Args:
        X: Feature DataFrame
        y: Target Series
        model_class: Model class untuk RFE
        n_features_to_select: Number of features to select
        cv_splits: Optional pre-computed CV splits
        n_splits: Number of CV splits jika cv_splits tidak provided
    
    Returns:
        List of selected feature names
    """
    from sklearn.feature_selection import RFE
    
    # Create model
    model = model_class()
    
    # RFE
    selector = RFE(model, n_features_to_select=n_features_to_select, step=1)
    selector.fit(X.values, y.values)
    
    # Get selected features
    selected_features = X.columns[selector.support_].tolist()
    
    return selected_features


def analyze_feature_correlation(features: pd.DataFrame,
                               threshold: float = 0.95) -> Dict:
    """
    Analyze feature correlation dan identify highly correlated pairs
    
    Args:
        features: Feature DataFrame
        threshold: Correlation threshold untuk flagging
    
    Returns:
        Dictionary dengan correlation analysis results
    """
    # Calculate correlation matrix
    corr_matrix = features.corr().abs()
    
    # Find highly correlated pairs
    high_corr_pairs = []
    for i in range(len(corr_matrix.columns)):
        for j in range(i+1, len(corr_matrix.columns)):
            corr_value = corr_matrix.iloc[i, j]
            if corr_value > threshold:
                high_corr_pairs.append({
                    'feature1': corr_matrix.columns[i],
                    'feature2': corr_matrix.columns[j],
                    'correlation': corr_value
                })
    
    # Recommend features to remove (keep feature dengan higher variance)
    features_to_remove = []
    for pair in high_corr_pairs:
        feat1_var = features[pair['feature1']].var()
        feat2_var = features[pair['feature2']].var()
        
        if feat1_var < feat2_var:
            features_to_remove.append(pair['feature1'])
        else:
            features_to_remove.append(pair['feature2'])
    
    # Remove duplicates
    features_to_remove = list(set(features_to_remove))
    
    return {
        'correlation_matrix': corr_matrix,
        'high_corr_pairs': high_corr_pairs,
        'features_to_remove': features_to_remove,
        'threshold': threshold
    }


def select_features_by_importance(features: pd.DataFrame,
                                  model,
                                  min_importance: float = 0.01,
                                  top_n: Optional[int] = None) -> List[str]:
    """
    Select features berdasarkan importance
    
    Args:
        features: Feature DataFrame
        model: Trained model dengan feature_importances_
        min_importance: Minimum importance threshold
        top_n: Select top N features (optional)
    
    Returns:
        List of selected feature names
    """
    if not hasattr(model, 'feature_importances_'):
        return features.columns.tolist()
    
    importance_df = calculate_feature_importance(model, features.columns.tolist())
    
    if top_n is not None:
        selected = importance_df.head(top_n)['feature'].tolist()
    else:
        selected = importance_df[importance_df['importance'] >= min_importance]['feature'].tolist()
    
    return selected


def remove_low_variance_features(features: pd.DataFrame,
                                threshold: float = 0.01) -> Tuple[pd.DataFrame, List[str]]:
    """
    Remove features dengan low variance
    
    Args:
        features: Feature DataFrame
        threshold: Variance threshold
    
    Returns:
        Filtered DataFrame dan list of removed features
    """
    variances = features.var()
    low_variance_features = variances[variances < threshold].index.tolist()
    
    filtered_features = features.drop(columns=low_variance_features)
    
    return filtered_features, low_variance_features


def comprehensive_feature_selection(features: pd.DataFrame,
                                   y: pd.Series,
                                   model_class,
                                   n_features_to_select: Optional[int] = None,
                                   min_importance: float = 0.01,
                                   correlation_threshold: float = 0.95,
                                   variance_threshold: float = 0.01) -> Dict:
    """
    Comprehensive feature selection dengan multiple methods
    
    Args:
        features: Feature DataFrame
        y: Target Series
        model_class: Model class untuk training
        n_features_to_select: Number of features to select (default: auto)
        min_importance: Minimum importance threshold
        correlation_threshold: Correlation threshold
        variance_threshold: Variance threshold
    
    Returns:
        Dictionary dengan selected features dan analysis
    """
    results = {
        'original_features': features.columns.tolist(),
        'selected_features': [],
        'removed_features': [],
        'steps': []
    }
    
    # Step 1: Remove low variance features
    filtered_features, removed_low_var = remove_low_variance_features(
        features, threshold=variance_threshold
    )
    results['steps'].append({
        'step': 'remove_low_variance',
        'removed': removed_low_var,
        'remaining': len(filtered_features.columns)
    })
    
    # Step 2: Remove highly correlated features
    corr_analysis = analyze_feature_correlation(
        filtered_features, threshold=correlation_threshold
    )
    if corr_analysis['features_to_remove']:
        filtered_features = filtered_features.drop(columns=corr_analysis['features_to_remove'])
        results['steps'].append({
            'step': 'remove_high_correlation',
            'removed': corr_analysis['features_to_remove'],
            'remaining': len(filtered_features.columns)
        })
    
    # Step 3: Train model dan get feature importance
    model = model_class()
    model.fit(filtered_features.values, y.values)
    
    # Step 4: Select features by importance
    if n_features_to_select is None:
        # Auto: select features dengan importance >= min_importance
        selected_features = select_features_by_importance(
            filtered_features, model, min_importance=min_importance
        )
    else:
        # Select top N features
        selected_features = select_features_by_importance(
            filtered_features, model, top_n=n_features_to_select
        )
    
    results['selected_features'] = selected_features
    results['removed_features'] = [
        f for f in results['original_features'] if f not in selected_features
    ]
    
    return results

