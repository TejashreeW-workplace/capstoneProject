import pandas as pd

def clean_transactions(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = raw_df.copy()
    # (a) drop exact duplicate rows
    df = df.drop_duplicates()
    
    # (b) strip surrounding spaces and convert to title case
    df['merchant_category'] = df['merchant_category'].astype(str).str.strip().str.title()
    df['city'] = df['city'].astype(str).str.strip().str.title()
    
    # (c) drop rows where amount_inr is missing
    df = df.dropna(subset=['amount_inr'])
    df = df[df['amount_inr'] != ""]
    df['amount_inr'] = pd.to_numeric(df['amount_inr'], errors='coerce')
    df = df.dropna(subset=['amount_inr'])
    
    # (d) drop rows where amount_inr is below 1 or above 1,000,000
    df = df[(df['amount_inr'] >= 1) & (df['amount_inr'] <= 1000000)]
    
    # (e) reset index
    df = df.reset_index(drop=True)
    return df

def add_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df['amount_inr'] = df['amount_inr'].astype(float)
    df['avg_amount_30d_inr'] = df['avg_amount_30d_inr'].astype(float)
    df['hour_of_day'] = df['hour_of_day'].astype(int)
    
    df['amount_vs_avg_ratio'] = df['amount_inr'] / df['avg_amount_30d_inr']
    df['is_night'] = df['hour_of_day'].apply(lambda h: 1 if h <= 5 else 0)
    df['high_value'] = df['amount_inr'].apply(lambda a: 1 if a > 50000 else 0)
    return df

if __name__ == "__main__":
    raw_df = pd.read_csv("transactions_raw.csv")
    print(f"Raw shape: {raw_df.shape[0]} rows, {raw_df.shape[1]} columns")
    
    dups = raw_df.duplicated().sum()
    print(f"Exact duplicate rows: {dups}")
    
    df_dedup = raw_df.drop_duplicates()
    missing_amt = (df_dedup['amount_inr'].isna() | (df_dedup['amount_inr'] == "")).sum()
    
    # Parse to check ranges safely
    amt_series = pd.to_numeric(df_dedup['amount_inr'], errors='coerce')
    out_of_range = ((amt_series < 1) | (amt_series > 1000000)).sum()
    missing_dist = (df_dedup['distance_from_home_km'].isna() | (df_dedup['distance_from_home_km'] == "")).sum()
    
    print(f"Missing amount_inr: {missing_amt}")
    print(f"Missing distance_from_home_km: {missing_dist}")
    print(f"Out of range amounts: {out_of_range}")
    
    print(f"Distinct merchant_category spellings: {raw_df['merchant_category'].nunique()}")
    print(f"Distinct city spellings: {raw_df['city'].nunique()}")
    
    cleaned = clean_transactions(raw_df)
    print(f"Cleaned table shape: {cleaned.shape[0]} rows")
    print(cleaned['merchant_category'].value_counts())
    print(cleaned['payment_mode'].value_counts())
    print(f"Min amount: {cleaned['amount_inr'].min()}, Max amount: {cleaned['amount_inr'].max()}")
    
    featured = add_features(cleaned)
    print(f"is_night sum: {featured['is_night'].sum()}")
    print(f"high_value sum: {featured['high_value'].sum()}")
    print(f"Max ratio: {featured['amount_vs_avg_ratio'].max():.2f}")
    
    fraud_count = featured['is_fraud'].sum()
    total_count = len(featured)
    print(f"Fraud rows: {fraud_count} of {total_count} ({fraud_count/total_count*100:.2f}%)")
    
    cb_1 = featured[featured['chargeback_filed'] == 1]
    cb_0 = featured[featured['chargeback_filed'] == 0]
    print(f"CB=1 count: {len(cb_1)}, fraud: {cb_1['is_fraud'].sum()}")
    print(f"CB=0 count: {len(cb_0)}, fraud: {cb_0['is_fraud'].sum()}")
