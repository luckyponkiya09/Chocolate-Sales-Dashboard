import pandas as pd


# 1. Total Revenue
def total_revenue(sales):
    return sales["Total Sales"].sum()


# 2. Total Orders
def total_orders(sales):
    return sales["Order_ID"].nunique()


# 3. Average Order Value
def average_order_value(sales):
    revenue = total_revenue(sales)
    orders = total_orders(sales)

    if orders == 0:
        return 0

    return revenue / orders


# 4. Country Revenue Rank
def country_revenue_rank(sales):
    country_sales = (
        sales.groupby("Country", dropna=False)["Total Sales"]
        .sum()
        .reset_index(name="Revenue")
    )

    country_sales["Rank"] = (
        country_sales["Revenue"]
        .rank(method="min", ascending=False)
        .astype("Int64")
    )

    return country_sales.sort_values(
        ["Rank", "Country"]
    ).reset_index(drop=True)


# 5. Delivery Success Percentage
def delivery_success_percentage(shipment):
    total = shipment["Order_ID"].nunique()

    delivered = shipment.loc[
        shipment["Shipment_Status"]
        .astype(str)
        .str.strip()
        .str.lower()
        .eq("delivered"),
        "Order_ID"
    ].nunique()

    if total == 0:
        return 0

    return (delivered / total) * 100