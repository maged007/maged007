"""
Train XGBoost price prediction model on Honda cars dataset.
"""
import os
import json
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from xgboost import XGBRegressor


def train_model():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(base_dir, 'data', 'honda_cars.csv')
    model_dir = os.path.join(base_dir, 'model')

    print(f"Loading data from: {csv_path}")
    df = pd.read_csv(csv_path)
    print(f"Dataset shape: {df.shape}")

    # Feature columns and target
    categorical_features = ['model', 'trim', 'category', 'engine', 'transmission', 'fuel_type', 'region_specs']
    numeric_features = ['year', 'mileage_km']
    all_features = categorical_features + numeric_features
    target = 'price_aed'

    # Drop rows with missing target
    df = df.dropna(subset=[target])
    df = df[df[target] > 0]

    print(f"\nEncoding categorical features...")
    encoders = {}
    df_encoded = df.copy()

    for col in categorical_features:
        le = LabelEncoder()
        df_encoded[col] = le.fit_transform(df[col].astype(str))
        encoders[col] = le
        print(f"  {col}: {len(le.classes_)} unique values")

    # Prepare X and y
    X = df_encoded[all_features].values
    y = df_encoded[target].values

    # Train/test split 80/20
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )
    print(f"\nTrain size: {len(X_train)}, Test size: {len(X_test)}")

    # Train XGBoost model
    print("\nTraining XGBoost model...")
    model = XGBRegressor(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        reg_alpha=0.1,
        reg_lambda=1.0,
        random_state=42,
        n_jobs=-1
    )
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False
    )

    # Evaluate
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    print(f"\n{'='*40}")
    print(f"MODEL PERFORMANCE METRICS")
    print(f"{'='*40}")
    print(f"MAE  (Mean Absolute Error):  {mae:,.0f} AED")
    print(f"RMSE (Root Mean Sq Error):   {rmse:,.0f} AED")
    print(f"R²   (R-squared Score):      {r2:.4f} ({r2*100:.2f}%)")
    print(f"{'='*40}")

    # Save model
    model_path = os.path.join(model_dir, 'honda_price_model.pkl')
    joblib.dump(model, model_path)
    print(f"\nModel saved to: {model_path}")

    # Save encoders
    encoders_path = os.path.join(model_dir, 'encoders.pkl')
    joblib.dump(encoders, encoders_path)
    print(f"Encoders saved to: {encoders_path}")

    # Save feature list
    features_path = os.path.join(model_dir, 'features.pkl')
    joblib.dump(all_features, features_path)
    print(f"Features saved to: {features_path}")

    # Save model stats
    stats = {
        'mae': round(mae, 2),
        'rmse': round(rmse, 2),
        'r2': round(r2, 4),
        'r2_percent': round(r2 * 100, 2),
        'training_date': datetime.now().isoformat(),
        'train_size': len(X_train),
        'test_size': len(X_test),
        'total_samples': len(df),
        'features': all_features,
        'categorical_features': categorical_features,
        'numeric_features': numeric_features
    }

    stats_path = os.path.join(model_dir, 'model_stats.json')
    with open(stats_path, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    print(f"Stats saved to: {stats_path}")

    # Save training data options for API
    options = {}
    for col in categorical_features:
        options[col] = sorted(df[col].astype(str).unique().tolist())
    options['year'] = sorted(df['year'].astype(int).unique().tolist())

    # Save per-model options (for dynamic filtering)
    model_options = {}
    for car_model in df['model'].unique():
        subset = df[df['model'] == car_model]
        model_options[car_model] = {
            'trim': sorted(subset['trim'].astype(str).unique().tolist()),
            'engine': sorted(subset['engine'].astype(str).unique().tolist()),
            'year': sorted(subset['year'].astype(int).unique().tolist()),
            'category': sorted(subset['category'].astype(str).unique().tolist()),
        }

    options['model_options'] = model_options

    options_path = os.path.join(model_dir, 'options.json')
    with open(options_path, 'w', encoding='utf-8') as f:
        json.dump(options, f, ensure_ascii=False, indent=2)
    print(f"Options saved to: {options_path}")

    print(f"\nAll model files saved successfully!")
    return stats


if __name__ == '__main__':
    stats = train_model()
