import os
import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import xgboost as xgb

def main():
    project_root = Path(__file__).resolve().parents[0]
    # In case it is copied to backend/ml/training/
    if "training" in project_root.parts or "ml" in project_root.parts:
        project_root = Path(__file__).resolve().parents[3]
    else:
        project_root = Path(__file__).resolve().parents[3]
        
    dataset_dir = project_root / "dataset"
    csv_path = dataset_dir / "merged_intrusion.csv"
    json_path = dataset_dir / "merged_intrusion.json"

    print("=" * 80)
    print("STEP 1: Loading datasets from dataset folder...")
    print("=" * 80)

    # 1. Load JSON file
    print(f"Loading JSON metadata: {json_path}")
    with open(json_path, 'r', encoding='utf-8') as f:
        json_data = json.load(f)
    print(f"JSON loaded successfully. Keys present: {list(json_data.keys())}")
    
    # Inspect json keys and identify target/label definitions
    print("\nInspecting JSON keys:")
    for k, v in json_data.items():
        if isinstance(v, list):
            print(f"  {k}: List of length {len(v)}")
        elif isinstance(v, dict):
            print(f"  {k}: Dict with keys {list(v.keys())}")
        else:
            print(f"  {k}: {type(v)}")

    # 2. Load CSV file
    print(f"\nLoading CSV dataset: {csv_path}")
    df_preview = pd.read_csv(csv_path, nrows=5)
    print("CSV Columns:")
    print(df_preview.columns.tolist())

    print("\n" + "=" * 80)
    print("STEP 2: Identifying target/label column...")
    print("=" * 80)
    target_col = "attack type"
    print(f"Target column identified in CSV: '{target_col}'")
    
    print("\n" + "=" * 80)
    print("STEP 3: Randomly sampling records for fast training...")
    print("=" * 80)
    print("Loading full CSV for sampling...")
    df = pd.read_csv(csv_path)
    print(f"Full dataset shape: {df.shape}")
    
    sample_size = 10000
    print(f"Sampling {sample_size} records randomly...")
    df_sample = df.sample(n=sample_size, random_state=42).copy()
    print(f"Sample shape: {df_sample.shape}")

    print("\n" + "=" * 80)
    print("STEP 4: Cleaning and preprocessing...")
    print("=" * 80)
    metadata_cols = ["source_dataset", target_col]
    feature_cols = [c for c in df_sample.columns if c not in metadata_cols]
    
    print(f"Number of feature columns: {len(feature_cols)}")
    
    X_sample = df_sample[feature_cols].copy()
    y_sample = df_sample[target_col].copy()

    # Handle infinite values
    print("Replacing infinite values with NaN...")
    X_sample.replace([np.inf, -np.inf], np.nan, inplace=True)
    
    # Handle missing values
    missing_count = X_sample.isnull().sum().sum()
    print(f"Missing values found: {missing_count}. Imputing missing values with 0.0...")
    X_sample.fillna(0.0, inplace=True)

    # Encode label column
    print("Encoding categorical labels...")
    label_encoder = LabelEncoder()
    y_encoded = label_encoder.fit_transform(y_sample)
    
    classes_mapping = {i: c for i, c in enumerate(label_encoder.classes_)}
    print("Classes Mapping:")
    for code, cls_name in classes_mapping.items():
        print(f"  {code} -> {cls_name}")

    print("\n" + "=" * 80)
    print("STEP 5: Splitting dataset and training XGBoost classifier...")
    print("=" * 80)
    X_train, X_test, y_train, y_test = train_test_split(
        X_sample, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
    )
    print(f"Training set: {X_train.shape}, Test set: {X_test.shape}")

    # Train XGBoost
    clf = xgb.XGBClassifier(
        n_estimators=100,
        max_depth=6,
        learning_rate=0.1,
        random_state=42,
        eval_metric="mlogloss",
        n_jobs=-1
    )
    
    print("Fitting model...")
    clf.fit(X_train, y_train)
    print("Model training complete.")

    print("\n" + "=" * 80)
    print("STEP 6: Evaluating model...")
    print("=" * 80)
    y_pred = clf.predict(X_test)
    y_pred_proba = clf.predict_proba(X_test)
    
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Test Accuracy: {accuracy:.4f}")
    
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=label_encoder.classes_, zero_division=0))
    
    print("Confusion Matrix:")
    conf_mat = confusion_matrix(y_test, y_pred)
    conf_df = pd.DataFrame(conf_mat, index=label_encoder.classes_, columns=label_encoder.classes_)
    print(conf_df)

    print("\n" + "=" * 80)
    print("STEP 7: Random test record prediction...")
    print("=" * 80)
    rng = np.random.default_rng(42)
    random_idx = rng.integers(0, len(X_test))
    
    test_record = X_test.iloc[[random_idx]]
    actual_label_encoded = y_test[random_idx]
    actual_label = label_encoder.classes_[actual_label_encoded]
    
    pred_encoded = clf.predict(test_record)[0]
    pred_label = label_encoder.classes_[pred_encoded]
    pred_proba = clf.predict_proba(test_record)[0]
    
    print(f"Record index in test split: {random_idx}")
    print(f"Actual label:    {actual_label}")
    print(f"Predicted label: {pred_label} (Confidence: {pred_proba[pred_encoded]:.4f})")

    print("\n" + "=" * 80)
    print("STEP 8: Saving model and label encoder...")
    print("=" * 80)
    models_dir = project_root / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    model_save_path = models_dir / "intrusion_xgboost.joblib"
    
    model_artifact = {
        "model": clf,
        "label_encoder": label_encoder,
        "feature_names": feature_cols
    }
    
    joblib.dump(model_artifact, model_save_path)
    print(f"Trained model and preprocessing encoders saved to: {model_save_path}")

    print("\n" + "=" * 80)
    print("STEP 9: Verifying saved model loading and prediction...")
    print("=" * 80)
    loaded_artifact = joblib.load(model_save_path)
    loaded_model = loaded_artifact["model"]
    loaded_le = loaded_artifact["label_encoder"]
    loaded_features = loaded_artifact["feature_names"]
    
    print("Model loaded successfully.")
    dummy_input = pd.DataFrame(np.zeros((1, len(loaded_features))), columns=loaded_features)
    dummy_pred_encoded = loaded_model.predict(dummy_input)[0]
    dummy_pred_label = loaded_le.classes_[dummy_pred_encoded]
    print(f"Dummy prediction works. Predicted label for zero input: {dummy_pred_label}")
    print("=" * 80)

if __name__ == "__main__":
    main()
