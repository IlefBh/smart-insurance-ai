# scripts/train_frequency.py

import pandas as pd
from src.models.frequency import train_frequency

DATA_PATH = "data/processed/business_df_with_governorate.csv"  # change if your file name differs

def main():
    print("Loading:", DATA_PATH)
    df = pd.read_csv(DATA_PATH)

    print("Training frequency model...")
    model, metrics = train_frequency(df)

    print("\n✅ Done.")
    print("Metrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
