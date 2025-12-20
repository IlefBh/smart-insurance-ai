# scripts/train_severity.py

import pandas as pd
from src.models.severity import train_severity

DATA_PATH = "data/processed/business_df_with_governorate.csv"  # adapte si besoin

def main():
    print("Loading:", DATA_PATH)
    df = pd.read_csv(DATA_PATH)

    model, metrics = train_severity(df)

    print("\n✅ Severity model trained.")
    print("Saved model to: artifacts/sklearn/severity_model.joblib")
    print("Saved metrics to: artifacts/sklearn/severity_metrics.json")

    print("\nMetrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
