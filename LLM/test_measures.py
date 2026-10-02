from app.data_loader import load_datasets, clean_datasets
from app.measures import (
    total_revenue,
    total_orders,
    average_order_value,
    country_revenue_rank,
    delivery_success_percentage
)

# Load data
data = clean_datasets(load_datasets())

sales = data["sales"]
shipment = data["shipment"]

# Calculate measures
print("TOTAL REVENUE:", total_revenue(sales))
print("TOTAL ORDERS:", total_orders(sales))
print("AVERAGE ORDER VALUE:", average_order_value(sales))

print("\nCOUNTRY REVENUE RANK:")
print(country_revenue_rank(sales).to_string(index=False))

print(
    "\nDELIVERY SUCCESS:",
    round(delivery_success_percentage(shipment), 2),
    "%"
)