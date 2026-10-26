import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, StratifiedKFold, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import precision_score, recall_score, f1_score, confusion_matrix
import prepare

def build_final_model():
    raw_df = pd.read_csv("transactions_raw.csv")
    cleaned = prepare.clean_transactions(raw_df)
    featured = prepare.add_features(cleaned)
    
    y = featured['is_fraud'].astype(int)
    X_raw = featured.drop(columns=['txn_id', 'customer_id', 'chargeback_filed', 'is_fraud'])
    
    # Enforce Pinned Order Execution
    numeric_binary_cols = [
        'amount_inr', 'hour_of_day', 'txn_count_last_24h', 'avg_amount_30d_inr',
        'distance_from_home_km', 'is_new_device', 'account_age_days'
    ]
    engineered_cols = ['amount_vs_avg_ratio', 'is_night', 'high_value']
    categorical_cols = ['merchant_category', 'city', 'payment_mode']
    
    X_num = X_raw[numeric_binary_cols + engineered_cols]
    X_cat = pd.get_dummies(X_raw[categorical_cols], dtype=int)
    # Sort category columns alphabetically group by group to maintain cross-environment deterministic behavior
    X_cat = X_cat[sorted(X_cat.columns)]
    
    X = pd.concat([X_num, X_cat], axis=1)
    feature_names = list(X.columns)
    
    # Train / Val / Test Stratified Splits
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=0.20, stratify=y, random_state=42
    )
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=0.25, stratify=y_train_val, random_state=42
    )
    
    # Compute median from training split only to prevent pipeline leakage
    train_median = pd.to_numeric(X_train['distance_from_home_km'], errors='coerce').median()
    
    for df_split in [X_train, X_val, X_test]:
        df_split['distance_from_home_km'] = pd.to_numeric(df_split['distance_from_home_km'], errors='coerce').fillna(train_median)
        
    # Model Setup
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    
    # Hyperparameter Grid Search for Random Forest
    rf_base = RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=42)
    param_grid = {
        'max_depth': [4, 6, 8, None],
        'min_samples_leaf': [5, 10, 20]
    }
    grid = GridSearchCV(rf_base, param_grid, cv=cv, scoring='f1', n_jobs=1)
    grid.fit(X_train, y_train)
    
    best_rf = grid.best_estimator_
    
    # Compute Decision Threshold Matrix Threshold Matrix
    val_probs = best_rf.predict_proba(X_val)[:, 1]
    thresholds = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
    t_star = 0.1
    
    for t in sorted(thresholds, reverse=True):
        preds = (val_probs >= t).astype(int)
        rec = recall_score(y_val, preds, zero_division=0)
        if rec >= 0.65:
            t_star = t
            break
            
    return {
        "model": best_rf,
        "columns": feature_names,
        "median": train_median,
        "threshold": t_star,
        "splits": (X_train, X_val, X_test, y_train, y_val, y_test)
    }

if __name__ == "__main__":
    res = build_final_model()
    X_train, X_val, X_test, y_train, y_val, y_test = res["splits"]
    print(f"Columns structural pinned list: {res['columns']}")
    print(f"Train size: {len(X_train)} (Fraud: {y_train.sum()})")
    print(f"Val size: {len(X_val)} (Fraud: {y_val.sum()})")
    print(f"Test size: {len(X_test)} (Fraud: {y_test.sum()})")
    print(f"Calculated Training Median: {res['median']}")
    print(f"Selected Optimal Threshold T_star: {res['threshold']}")
