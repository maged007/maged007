"""
Parse honda_cars.md and extract the table rows to honda_cars.csv
"""
import re
import csv
import os


def parse_honda_cars_md(md_path, csv_path):
    """Parse the markdown file and extract table data to CSV."""

    columns = [
        'id', 'model', 'year', 'trim', 'category',
        'mileage_km', 'engine', 'transmission', 'fuel_type',
        'color', 'region_specs', 'price_aed', 'price_sar'
    ]

    rows = []

    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()

        # Skip non-table lines, header, and separator rows
        if not line.startswith('|'):
            continue

        # Skip separator rows (contain ---)
        if '---' in line:
            continue

        # Split by | and strip whitespace
        parts = [p.strip() for p in line.split('|')]
        # Remove empty first and last elements (from leading/trailing |)
        parts = [p for p in parts if p != '']

        # Must have exactly 13 columns
        if len(parts) != 13:
            continue

        # Skip header row (first column is '#' not a number)
        try:
            row_id = int(parts[0])
        except ValueError:
            continue

        # Extract fields
        id_val = parts[0]
        model = parts[1]       # e.g. "Honda Accord"
        year = parts[2]        # e.g. "2018"
        trim = parts[3]        # e.g. "LX"
        category = parts[4]    # e.g. "سيدان متوسطة"

        # Mileage - remove commas
        mileage_str = parts[5].replace(',', '').strip()
        try:
            mileage_km = int(mileage_str)
        except ValueError:
            mileage_km = 0

        engine = parts[6]          # e.g. "1.5L توربو"
        transmission = parts[7]    # e.g. "CVT"
        fuel_type = parts[8]       # e.g. "بنزين"
        color = parts[9]           # e.g. "رمادي فضي"
        region_specs = parts[10]   # e.g. "مواصفات خليجية (GCC)"

        # Prices - remove commas
        price_aed_str = parts[11].replace(',', '').strip()
        price_sar_str = parts[12].replace(',', '').strip()

        try:
            price_aed = int(price_aed_str)
        except ValueError:
            price_aed = 0

        try:
            price_sar = int(price_sar_str)
        except ValueError:
            price_sar = 0

        rows.append([
            id_val, model, year, trim, category,
            mileage_km, engine, transmission, fuel_type,
            color, region_specs, price_aed, price_sar
        ])

    # Write CSV
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)

    return len(rows)


if __name__ == '__main__':
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    md_path = os.path.join(base_dir, 'honda_cars.md')
    csv_path = os.path.join(base_dir, 'data', 'honda_cars.csv')

    print(f"Parsing: {md_path}")
    count = parse_honda_cars_md(md_path, csv_path)
    print(f"Saved {count} rows to: {csv_path}")

    # Verify
    import pandas as pd
    df = pd.read_csv(csv_path)
    print(f"\nDataset shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"\nSample data:")
    print(df.head(3).to_string())
    print(f"\nModels in dataset: {sorted(df['model'].unique())}")
    print(f"Year range: {df['year'].min()} - {df['year'].max()}")
    print(f"Price AED range: {df['price_aed'].min():,} - {df['price_aed'].max():,}")
