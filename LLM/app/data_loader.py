import pandas as pd
from pathlib import Path

DATA_DIR = Path("D:\\projects\\Chocolate-Sales-Dashboard\\Dataset")

def load_datasets():
    return {
        "sales": pd.read_excel(
            DATA_DIR / "Chocolate main Data.xlsx"
        ),
        "country": pd.read_excel(
            DATA_DIR / "Country.xlsx"
        ),
        "products": pd.read_excel(
            DATA_DIR / "Products.xlsx"
        ),
        "region": pd.read_excel(
            DATA_DIR / "Region.xlsx"
        ),
        "salesperson": pd.read_excel(
            DATA_DIR / "Sales Person.xlsx"
        ),
        "shipment": pd.read_excel(
            DATA_DIR / "Shipment.xlsx"
        )
    }

def clean_datasets(datasets):
    for name, df in datasets.items():
        df.columns = (
            df.columns.astype(str)
            .str.strip()
        )

    sales = datasets["sales"]
    sales["Order_ID"] = sales["Order_ID"].astype(str).str.strip()
    sales["Total Sales"] = pd.to_numeric(
        sales["Total Sales"], errors="coerce"
    )

    return datasets