# scripts/train_segmentation.py

import pandas as pd
from src.models.segmentation import train_segmentation

DATA_PATH = "data/processed/business_df_with_governorate.csv"  # change if your file name is different

def main():
    print("Loading:", DATA_PATH)
    df = pd.read_csv(DATA_PATH)

    print("Training segmentation...")
    best_k, scores = train_segmentation(df)

    print("\n✅ Done")
    print("Chosen K:", best_k)
    print("Silhouette scores:")
    for k, v in scores.items():
        print(f"  K={k}: {v:.4f}")

if __name__ == "__main__":
    main()
