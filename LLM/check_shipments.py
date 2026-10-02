
import pandas as pd
from pathlib import Path

# Find Excel files
files = list(Path(".").glob("*.xlsx"))

print("Excel files found:")
for file in files:
    print(file.name)

# Enter your actual shipment Excel filename
shipment_file = r"D:\projects\Chocolate-Sales-Dashboard\Dataset\Shipment.xlsx"

# Load shipment data
df = pd.read_excel(shipment_file)

# Remove extra spaces from all column names
df.columns = df.columns.str.strip()

print("\nCleaned columns:")
print(df.columns.tolist())

# Check duplicate order records
print("\n--- DUPLICATE ORDER CHECK ---")

duplicate_rows = df[df.duplicated(subset=["Order_ID"], keep=False)]

print("Total shipment rows:", len(df))
print("Unique order IDs:", df["Order_ID"].nunique())
print("Rows belonging to duplicated order IDs:", len(duplicate_rows))
print(
    "Number of duplicated order IDs:",
    duplicate_rows["Order_ID"].nunique()
)

# Check orders having multiple shipment statuses
print("\n--- CONFLICTING STATUS CHECK ---")

status_counts = df.groupby("Order_ID")["Shipment_Status"].nunique()

conflicting_orders = status_counts[status_counts > 1]

print("Orders with multiple statuses:", len(conflicting_orders))

if len(conflicting_orders) > 0:
    print("\nExamples of conflicting orders:")
    print(
        df[df["Order_ID"].isin(conflicting_orders.index)]
        [["Order_ID", "Shipment_Status"]]
        .sort_values("Order_ID")
        .head(30)
    )
else:
    print("No orders have multiple shipment statuses.")

# Show overall status counts
print("\n--- STATUS COUNTS ---")
print(df["Shipment_Status"].value_counts(dropna=False))

# Inspect duplicated order records
print("\n--- DUPLICATED ORDER DETAILS ---")

if not duplicate_rows.empty:
    print(
        duplicate_rows.sort_values("Order_ID").to_string(index=False)
    )
else:
    print("No duplicate records found.")
