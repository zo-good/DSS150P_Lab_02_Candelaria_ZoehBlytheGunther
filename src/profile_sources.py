"""Week 2 starter: profile CSV, JSON, Parquet, API payload, and PostgreSQL table.
Complete the TODOs. Do not hard-code expected counts.
"""
import pandas as pd

from pathlib import Path
import json, csv
DATA_DIR=Path(__file__).resolve().parents[1]/'data'

def profile_csv(path):
       file_size = path.stat().st_size
       df = pd.read_csv(path)
       n_rows, n_cols = df.shape

       print(f"=== Profiling {path.name} ===")
       print(f"File size: {file_size:,} bytes")
       print(f"Rows: {n_rows}, Columns: {n_cols}")

       print("\nColumns and pandas-inferred dtype:")
       for col in df.columns:
        print(f"  {col}: {df[col].dtype}")

       print("\nMissing values by column:")
       print(df.isna().sum())

       exact_dupes = df.duplicated().sum()
       print(f"\nExact duplicate rows: {exact_dupes}")

       dupe_ids = df['customer_id'].duplicated().sum()
       print(f"Duplicate customer_id values: {dupe_ids}")
       print(f"customer_id unique: {dupe_ids == 0}")

       return df

def profile_json(path):
    file_size = path.stat().st_size
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    print(f"=== Profiling {path.name} ===")
    print(f"File size: {file_size:,} bytes")
    print(f"Root type: {type(data).__name__}")
    print(f"Record count: {len(data)}")

    all_keys = set()
    for record in data:
        all_keys.update(record.keys())
    print(f"\nTop-level keys observed: {sorted(all_keys)}")

    nested_keys = set()
    for record in data:
        for k, v in record.items():
            if isinstance(v, dict):
                nested_keys.add(k)
    print(f"Nested (object) fields: {sorted(nested_keys)}")

    missing_counts = {k: 0 for k in all_keys}
    for record in data:
        for k in all_keys:
            if k not in record or record[k] is None:
                missing_counts[k] += 1
    print("\nMissing/null counts by key:")
    for k, v in missing_counts.items():
        print(f"  {k}: {v}")

    print("\nField types (from first record containing each key):")
    for k in sorted(all_keys):
        for record in data:
            if k in record and record[k] is not None:
                print(f"  {k}: {type(record[k]).__name__}")
                break

    return data

def profile_parquet(path):
    file_size = path.stat().st_size
    df = pd.read_parquet(path)
    n_rows, n_cols = df.shape

    print(f"=== Profiling {path.name} ===")
    print(f"File size: {file_size:,} bytes")
    print(f"Rows: {n_rows}, Columns: {n_cols}")

    print("\nColumns and dtype (from Parquet's stored schema):")
    print(df.dtypes)

    print("\nMissing values by column:")
    print(df.isna().sum())

    csv_path = path.parent / 'products_optional_compare.csv'
    json_path = path.parent / 'products_optional_compare.json'

    if csv_path.exists():
        df_csv = pd.read_csv(csv_path)
        print(f"\n--- Same data as {csv_path.name} ---")
        print(f"File size: {csv_path.stat().st_size:,} bytes")
        print("Dtypes pandas had to GUESS from text:")
        print(df_csv.dtypes)

    if json_path.exists():
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        df_json = pd.DataFrame(data)
        print(f"\n--- Same data as {json_path.name} ---")
        print(f"File size: {json_path.stat().st_size:,} bytes")
        print("Dtypes pandas had to GUESS from text:")
        print(df_json.dtypes)

    return df

if __name__=='__main__':
    profile_csv(DATA_DIR/'customers.csv')
    profile_json(DATA_DIR/'orders.json')
    profile_parquet(DATA_DIR/'products.parquet')
