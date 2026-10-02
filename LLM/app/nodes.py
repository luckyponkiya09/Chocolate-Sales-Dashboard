
import os
from urllib import response
import pandas as pd
from typing import Any
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace

from app.state import BusinessState

load_dotenv()

# Project data directory
DATA_DIR = r"D:\projects\Chocolate-Sales-Dashboard\Dataset"

# --------------------------------------------------
# Helper: Load Excel datasets
# --------------------------------------------------


def load_datasets():
    """Load all Excel datasets used by the dashboard."""

    files = {
        "sales": "Chocolate main Data.xlsx",
        "country": "Country.xlsx",
        "products": "Products.xlsx",
        "region": "Region.xlsx",
        "sales_person": "Sales Person.xlsx",
        "shipment": "Shipment.xlsx",
    }

    datasets = {}

    for key, filename in files.items():
        path = os.path.join(DATA_DIR, filename)

        if os.path.exists(path):
            datasets[key] = pd.read_excel(path)

            # Clean extra spaces from column names
            datasets[key].columns = datasets[key].columns.str.strip()

            # Remove exact duplicate rows from shipment data
            if key == "shipment":
                before = len(datasets[key])

                datasets[key] = datasets[key].drop_duplicates()

                after = len(datasets[key])

                print(
                    f"Removed {before - after} exact duplicate "
                    f"shipment rows."
                )
                print(f"Clean shipment rows: {after}")

        else:
            print(f"Warning: File not found: {path}")
            datasets[key] = pd.DataFrame()

    return datasets


# --------------------------------------------------
# Helper: Clean column names
# --------------------------------------------------

def clean_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names for easier matching."""

    df = df.copy()
    df.columns = [
        str(col).strip()
        for col in df.columns
    ]
    return df


def find_column(df: pd.DataFrame, candidates: list[str]):
    """Find a column using case-insensitive candidate names."""

    normalized = {
        str(col).strip().lower(): col
        for col in df.columns
    }

    for candidate in candidates:
        if candidate.lower() in normalized:
            return normalized[candidate.lower()]

    return None


def numeric_sum(df: pd.DataFrame, candidates: list[str]) -> float:
    """Safely sum a numeric column."""

    column = find_column(df, candidates)

    if column is None:
        return 0.0

    values = pd.to_numeric(df[column], errors="coerce")
    return float(values.sum())


# --------------------------------------------------
# Node 1: Classify the user's question
# --------------------------------------------------



def classify_question(state: BusinessState) -> dict:
    """Identify the metric requested by the user."""

    question = state.get("question", "").lower().strip()

    print("CLASSIFIER QUESTION:", question)

    # 1. Monthly salesperson revenue analysis
    monthly_terms = [
        "month by month",
        "monthly revenue",
        "monthly sales",
        "month-wise revenue",
        "revenue trend",
        "monthly performance",
        "each month",
        "per month",
    ]

    salesperson_terms = [
        "salesperson",
        "sales person",
        "salespeople",
        "sales rep",
        "sales representative",
    ]

    if (
        any(term in question for term in monthly_terms)
        and (
            any(term in question for term in salesperson_terms)
            or "revenue" in question
        )
    ):
        intent = "salesperson_monthly"

    # 2. Delivery analysis
    elif (
        any(term in question for term in [
            "delivery", "deliveries", "shipment",
            "shipping", "shipped"
        ])
        and any(term in question for term in [
            "success", "successful", "failure",
            "failed", "performance", "rate",
            "delivered", "status"
        ])
    ):
        intent = "delivery_success"

    # 3. Average order value
    elif any(term in question for term in [
        "average order value",
        "average value per order",
        "aov",
    ]):
        intent = "average_order_value"

    # 4. Top salesperson / salesperson ranking
    elif (
        any(term in question for term in [
            "salesperson",
            "sales person",
            "salespeople",
            "sales persons",
            "sales rep",
            "sales representative",
            "sales representatives",
            "who generated the highest revenue",
            "who generated the most revenue",
            "who has the highest revenue",
            "who has the most revenue",
            "highest revenue employee",
            "top performer",
            "top performing salesperson",
            "best performing salesperson",
            "rank salespeople",
            "rank sales persons",
            "top 5 sales",
            "top five sales",
        ])
    ):
        intent = "top_salesperson"

    # 5. Top product
    elif any(term in question for term in [
        "which product",
        "top product",
        "best-selling product",
        "best selling product",
        "highest revenue product",
        "product generates the most",
        "top 5 products",
        "top five products",
    ]):
        intent = "top_product"

    # 6. Top country
    elif any(term in question for term in [
        "which country",
        "top country",
        "highest revenue country",
        "country generates the most",
        "compare revenue across countries",
        "revenue by country",
        "sales by country",
    ]):
        intent = "top_country"

    # 7. Total orders
    elif any(term in question for term in [
        "total orders",
        "number of orders",
        "how many orders",
        "count of orders",
    ]):
        intent = "total_orders"

    # 8. Total revenue
    elif any(term in question for term in [
        "total revenue",
        "total sales",
        "overall revenue",
        "how much revenue",
        "revenue generated",
    ]):
        intent = "total_revenue"

    # 9. Damage risk / priority questions
    elif any(term in question for term in [
        "damage risk",
        "damage-risk",
        "risk level",
        "risk breakdown",
        "priority",
        "urgent shipments",
        "high priority",
        "low priority",
    ]):
        # These currently use the delivery analysis calculation.
        intent = "delivery_success"

    else:
        intent = "general"

    dataset_map = {
        "total_revenue": ["sales"],
        "total_orders": ["sales"],
        "average_order_value": ["sales"],
        "top_country": ["sales"],
        "top_product": ["sales"],
        "top_salesperson": ["sales"],
        "delivery_success": ["shipment"],
        "salesperson_monthly": ["sales"],
        "general": ["sales", "shipment"],
    }

    selected_datasets = dataset_map[intent]

    print("CLASSIFIER INTENT:", intent)
    print("SELECTED DATASETS:", selected_datasets)

    return {
        "intent": intent,
        "selected_datasets": selected_datasets,
    }

# Node 2: Retrieve the required datasets

def retrieve_data(state: BusinessState) -> dict:
    """Load the datasets selected by the classifier."""

    datasets = load_datasets()

    selected = state.get("selected_datasets", ["sales"])

    retrieved = {
        name: clean_columns(datasets[name])
        for name in selected
        if name in datasets
    }

    return {
        "sales_data": retrieved
    }

# Node 3: Calculate requested metric

def calculate_requested_metric(state: BusinessState) -> dict:
    """Calculate the metric requested by the user."""

    intent = state.get("intent", "general")
    data = state.get("sales_data", {})

    sales = data.get("sales", pd.DataFrame())
    shipment = data.get("shipment", pd.DataFrame())

    # --------------------------------------------------
    # DELIVERY ANALYSIS
    # --------------------------------------------------
    if intent == "delivery_success":

        if shipment.empty:
            return {"analysis": {"error": "Shipment data is unavailable."}}

        shipment_copy = shipment.copy()
        shipment_copy.columns = shipment_copy.columns.str.strip()
        shipment_copy = shipment_copy.drop_duplicates()

        status_col = find_column(
            shipment_copy,
            ["Shipment_Status", "Shipment Status",
             "Delivery Status", "Status"]
        )

        order_col = find_column(
            shipment_copy,
            ["Order_ID", "Order ID", "Order Number"]
        )

        if status_col is None:
            return {"analysis": {"error": "Delivery status column was not found."}}

        # Normalize status values
        shipment_copy[status_col] = (
            shipment_copy[status_col]
            .astype(str)
            .str.strip()
            .str.lower()
        )

        delivered_rows = shipment_copy[
            shipment_copy[status_col] == "delivered"
        ]

        if order_col:
            total = shipment_copy[order_col].nunique()
            successful = delivered_rows[order_col].nunique()
            status_breakdown = (
                shipment_copy.groupby(status_col)[order_col]
                .nunique()
                .to_dict()
            )
        else:
            total = len(shipment_copy)
            successful = len(delivered_rows)
            status_breakdown = shipment_copy[status_col].value_counts().to_dict()

        rate = successful / total * 100 if total else 0

        question = state.get("question", "").lower()

        # Detect requested dimensions
        carrier_requested = any(
            word in question
            for word in ["carrier", "courier", "delivery partner"]
        )

        priority_requested = any(
            word in question
            for word in ["priority", "urgent", "high", "medium", "low"]
        )

        risk_requested = any(
            word in question
            for word in ["damage risk", "damage", "risk level", "risk category"]
        )

        carrier_breakdown = {}
        priority_breakdown = {}
        damage_risk_breakdown = {}
        combined_breakdown = {}

        # --------------------------------------------------
        # CARRIER + PRIORITY COMBINED ANALYSIS
        # --------------------------------------------------
        if carrier_requested and priority_requested:

            carrier_col = find_column(
                shipment_copy,
                ["Carrier", "Courier", "Delivery Partner"]
            )

            priority_col = find_column(
                shipment_copy,
                ["Delivery_Priority", "Delivery Priority", "Priority"]
            )

            if carrier_col is None or priority_col is None:
                return {
                    "analysis": {
                        "error": "Carrier or priority column was not found."
                    }
                }

            # Detect the requested priority as a whole word.
            # This prevents accidental matches such as "high" inside
            # unrelated words.
            import re

            priority_value = None

            for value in ["urgent", "high", "medium", "low"]:
                if re.search(rf"\b{value}\b", question):
                    priority_value = value
                    break

            if priority_value is None:
                return {
                    "analysis": {
                        "error": (
                            "Please specify a priority such as "
                            "urgent, high, medium, or low."
                        )
                    }
                }

            # Normalize priority values in the dataset
            priority_series = (
                shipment_copy[priority_col]
                .astype(str)
                .str.strip()
                .str.lower()
            )

            filtered = shipment_copy[
                priority_series == priority_value
            ].copy()

            # Calculate carrier results only for the selected priority
            for carrier, group in filtered.groupby(
                carrier_col,
                dropna=False
            ):
                if order_col:
                    total_orders = group[order_col].nunique()
                    delivered_orders = group.loc[
                        group[status_col] == "delivered",
                        order_col
                    ].nunique()
                else:
                    total_orders = len(group)
                    delivered_orders = int(
                        (group[status_col] == "delivered").sum()
                    )

                combined_breakdown[str(carrier)] = {
                    "total_orders": int(total_orders),
                    "delivered_orders": int(delivered_orders),
                    "success_rate": round(
                        delivered_orders / total_orders * 100,
                        2
                    ) if total_orders else 0
                }

            # Useful for checking whether the correct subset was selected
            combined_total = (
                filtered[order_col].nunique()
                if order_col else len(filtered)
            )

        else:
            priority_value = None
            combined_total = None

        # --------------------------------------------------
        # CARRIER BREAKDOWN
        # --------------------------------------------------
        if carrier_requested:
            carrier_col = find_column(
                shipment_copy,
                ["Carrier", "Courier", "Delivery Partner"]
            )

            if carrier_col:
                for carrier, group in shipment_copy.groupby(
                    carrier_col,
                    dropna=False
                ):
                    if order_col:
                        total_orders = group[order_col].nunique()
                        delivered_orders = group.loc[
                            group[status_col] == "delivered",
                            order_col
                        ].nunique()
                    else:
                        total_orders = len(group)
                        delivered_orders = int(
                            (group[status_col] == "delivered").sum()
                        )

                    carrier_breakdown[str(carrier)] = {
                        "total_orders": int(total_orders),
                        "delivered_orders": int(delivered_orders),
                        "success_rate": round(
                            delivered_orders / total_orders * 100,
                            2
                        ) if total_orders else 0
                    }

        # --------------------------------------------------
        # PRIORITY BREAKDOWN
        # --------------------------------------------------
        if priority_requested:
            priority_col = find_column(
                shipment_copy,
                ["Delivery_Priority", "Delivery Priority", "Priority"]
            )

            if priority_col:
                for priority, group in shipment_copy.groupby(
                    priority_col,
                    dropna=False
                ):
                    if order_col:
                        total_orders = group[order_col].nunique()
                        delivered_orders = group.loc[
                            group[status_col] == "delivered",
                            order_col
                        ].nunique()
                    else:
                        total_orders = len(group)
                        delivered_orders = int(
                            (group[status_col] == "delivered").sum()
                        )

                    priority_breakdown[
                        str(priority) if pd.notna(priority) else "Unknown"
                    ] = {
                        "total_orders": int(total_orders),
                        "delivered_orders": int(delivered_orders),
                        "success_rate": round(
                            delivered_orders / total_orders * 100,
                            2
                        ) if total_orders else 0
                    }

        # --------------------------------------------------
        # DAMAGE RISK BREAKDOWN
        # --------------------------------------------------
        if risk_requested:
            risk_col = find_column(
                shipment_copy,
                ["Damage_Risk", "Damage Risk", "Risk"]
            )

            if risk_col:
                for risk, group in shipment_copy.groupby(
                    risk_col,
                    dropna=False
                ):
                    if order_col:
                        total_orders = group[order_col].nunique()
                        delivered_orders = group.loc[
                            group[status_col] == "delivered",
                            order_col
                        ].nunique()
                    else:
                        total_orders = len(group)
                        delivered_orders = int(
                            (group[status_col] == "delivered").sum()
                        )

                    damage_risk_breakdown[
                        str(risk) if pd.notna(risk) else "Unknown"
                    ] = {
                        "total_orders": int(total_orders),
                        "delivered_orders": int(delivered_orders),
                        "success_rate": round(
                            delivered_orders / total_orders * 100,
                            2
                        ) if total_orders else 0
                    }

        # --------------------------------------------------
        # REPORT FOCUS
        # --------------------------------------------------
        if carrier_requested and priority_requested:
            report_focus = "combined_carrier_priority"
        elif carrier_requested:
            report_focus = "carrier"
        elif priority_requested:
            report_focus = "priority"
        elif risk_requested:
            report_focus = "damage_risk"
        else:
            report_focus = "overall"

        return {
            "analysis": {
                "delivery_success_percentage": round(rate, 2),
                "delivered_orders": int(successful),
                "total_shipments": int(total),
                "other_status_count": int(total - successful),
                "status_breakdown": status_breakdown,
                "carrier_breakdown": carrier_breakdown,
                "priority_breakdown": priority_breakdown,
                "damage_risk_breakdown": damage_risk_breakdown,
                "combined_breakdown": combined_breakdown,
                "selected_priority": priority_value,
                "combined_total": combined_total,
                "report_focus": report_focus
            }
        }

    # --------------------------------------------------
    # SALES ANALYSIS
    # --------------------------------------------------
    if sales.empty:
        return {"analysis": {"error": "Sales data is unavailable."}}

    sales = sales.copy()
    sales.columns = sales.columns.str.strip()

    revenue_col = find_column(
        sales,
        ["Total Sales", "Revenue", "Sales"]
    )

    order_col = find_column(
        sales,
        ["Order_ID", "Order ID", "Order Number"]
    )

    if intent in [
        "total_revenue",
        "average_order_value",
        "top_country",
        "top_product",
        "top_salesperson"
    ] and revenue_col is None:
        return {"analysis": {"error": "Revenue column was not found."}}
    # Total revenue
    if intent == "total_revenue":
        revenue = pd.to_numeric(
            sales[revenue_col],
            errors="coerce"
        ).sum()

        return {
            "analysis": {
                "total_revenue": float(revenue)
            }
        }

    # Total orders
    if intent == "total_orders":
        if order_col is None:
            return {"analysis": {"error": "Order ID column was not found."}}

        return {
            "analysis": {
                "total_orders": int(sales[order_col].nunique())
            }
        }

    # Average order value
    if intent == "average_order_value":
        if order_col is None:
            return {"analysis": {"error": "Order ID column was not found."}}

        revenue = pd.to_numeric(
            sales[revenue_col],
            errors="coerce"
        ).sum()

        orders = sales[order_col].nunique()

        return {
            "analysis": {
                "average_order_value": (
                    float(revenue / orders) if orders else 0
                ),
                "total_revenue": float(revenue),
                "total_orders": int(orders)
            }
        }

    # Top country or product
    # Top salespeople
    # Monthly revenue for a specific salesperson
    if intent == "salesperson_monthly":

        salesperson_col = find_column(
            sales,
            ["Sales Person", "Salesperson", "Sales Person Name"]
        )

        date_col = find_column(
            sales,
            ["Date", "Order Date", "Sales Date"]
        )

        if salesperson_col is None:
            return {
                "analysis": {
                    "error": "Salesperson column was not found."
                }
            }

        if date_col is None:
            return {
                "analysis": {
                    "error": "Date column was not found."
                }
            }

        # Extract the salesperson's name from the question
        question = state.get("question", "")

        # Find matching salesperson names in the dataset
        names = sales[salesperson_col].dropna().unique()

        matched_names = [
            name for name in names
            if str(name).lower() in question.lower()
        ]

        if not matched_names:
            return {
                "analysis": {
                    "error": (
                        "Could not identify a salesperson from "
                        "the question. Please provide their full name."
                    )
                }
            }

        salesperson = matched_names[0]

        # Filter the selected salesperson
        person_sales = sales[
            sales[salesperson_col] == salesperson
        ].copy()

        # Convert dates and revenue
        person_sales[date_col] = pd.to_datetime(
            person_sales[date_col],
            errors="coerce"
        )

        person_sales[revenue_col] = pd.to_numeric(
            person_sales[revenue_col],
            errors="coerce"
        )

        person_sales = person_sales.dropna(
            subset=[date_col, revenue_col]
        )

        # Group revenue by calendar month
        person_sales["Month"] = (
            person_sales[date_col].dt.to_period("M")
        )

        monthly = (
            person_sales.groupby("Month")[revenue_col]
            .sum()
            .sort_index()
        )

        if monthly.empty:
            return {
                "analysis": {
                    "error": "No monthly revenue data was available."
                }
            }

        monthly_revenue = {
            str(month): float(value)
            for month, value in monthly.items()
        }

        return {
            "analysis": {
                "salesperson": str(salesperson),
                "monthly_revenue": monthly_revenue,
                "total_revenue": float(monthly.sum()),
                "highest_month": str(monthly.idxmax()),
                "highest_month_revenue": float(monthly.max()),
                "lowest_month": str(monthly.idxmin()),
                "lowest_month_revenue": float(monthly.min())
            }
        }
    if intent == "top_salesperson":
        salesperson_col = find_column(
            sales,
            ["Sales Person", "Salesperson", "Sales Person Name"]
        )

        if salesperson_col is None:
            return {
                "analysis": {
                    "error": "Salesperson column was not found."
                }
            }

        sales[revenue_col] = pd.to_numeric(
            sales[revenue_col],
            errors="coerce"
        )

        grouped = (
            sales.groupby(salesperson_col)[revenue_col]
            .sum()
            .sort_values(ascending=False)
        )

        if grouped.empty:
            return {
                "analysis": {
                    "error": "No salesperson revenue data was available."
                }
            }

        top_n = grouped.head(5)

        return {
            "analysis": {
                "top_item": str(grouped.index[0]),
                "top_item_revenue": float(grouped.iloc[0]),
                "ranking": {
                    str(name): float(value)
                    for name, value in grouped.items()
                },
            }
        }
    if intent in ["top_country", "top_product"]:
        candidates = (
            ["Country", "Country Name"]
            if intent == "top_country"
            else [
                "Product",
                "Product Name",
                "Product_ID",
                "Product ID"
            ]
        )

        group_col = find_column(sales, candidates)

        if group_col is None:
            return {
                "analysis": {
                    "error": f"Grouping column not found for {intent}."
                }
            }

        sales[revenue_col] = pd.to_numeric(
            sales[revenue_col],
            errors="coerce"
        )

        grouped = (
            sales.groupby(group_col)[revenue_col]
            .sum()
            .sort_values(ascending=False)
        )

        if grouped.empty:
            return {"analysis": {"error": "No revenue data was available."}}

        return {
            "analysis": {
                "top_item": str(grouped.index[0]),
                "top_item_revenue": float(grouped.iloc[0]),
                "ranking": {
                    str(name): float(value)
                    for name, value in grouped.items()
                }
            }
        }

    # General sales overview
    revenue = (
        pd.to_numeric(sales[revenue_col], errors="coerce").sum()
        if revenue_col else None
    )

    orders = (
        int(sales[order_col].nunique())
        if order_col else None
    )

    return {
        "analysis": {
            "total_revenue": (
                float(revenue) if revenue is not None else None
            ),
            "total_orders": orders
        }
    }

# Node 4: Calculate business metrics

def calculate_metrics(state: BusinessState) -> dict:
    """LangGraph node wrapper for requested metric calculation."""
    return calculate_requested_metric(state)


# Node 5: Investigate findings


def investigate_findings(state: BusinessState) -> dict:
    """Create findings based on the requested metric."""

    metrics = state.get("analysis", {})
    report_focus = metrics.get("report_focus", "overall")
    intent = state.get("intent", "general")
    findings = []

    if metrics.get("error"):
        return {"findings": [metrics["error"]]}

    if intent == "total_revenue":
        revenue = metrics.get("total_revenue")
        if revenue is not None:
            findings.append(
                f"Total revenue is {revenue:,.2f}."
            )

    elif intent == "total_orders":
        orders = metrics.get("total_orders")
        if orders is not None:
            findings.append(
                f"There are {orders:,} distinct orders."
            )

    elif intent == "average_order_value":
        aov = metrics.get("average_order_value")
        if aov is not None:
            findings.append(
                f"Average order value is {aov:,.2f}."
            )
    
    elif intent == "top_salesperson":
        ranking = metrics.get("ranking", {})

        if ranking:
            # Sort by revenue, highest first.
            sorted_salespeople = sorted(
                ranking.items(),
                key=lambda item: item[1],
                reverse=True,
            )

            top_name, top_revenue = sorted_salespeople[0]

            findings.append(
                f"{top_name} generated the highest revenue, "
                f"at {top_revenue:,.2f}."
            )

            # Include up to five salespeople for comparison.
            top_five = sorted_salespeople[:5]

            comparison = "; ".join(
                f"{name}: {revenue:,.2f}"
                for name, revenue in top_five
            )

            findings.append(
                f"Top {len(top_five)} salespeople by revenue: "
                f"{comparison}."
            )
        else:
            findings.append(
                "No salesperson revenue ranking was available."
            )

    elif intent in ["top_product", "top_country"]:
        item = metrics.get("top_item")
        revenue = metrics.get("top_item_revenue")
        ranking = metrics.get("ranking", {})

        if item is not None and revenue is not None:
            label = (
                "product" if intent == "top_product"
                else "country"
            )

            findings.append(
                f"{item} has the highest revenue among the "
                f"{label}s, at {revenue:,.2f}."
            )

            # Include the top three entries for context.
            top_three = list(ranking.items())[:3]

            if len(top_three) > 1:
                comparison = "; ".join(
                    f"{name}: {value:,.2f}"
                    for name, value in top_three
                )
                findings.append(
                    f"Top three {label}s by revenue: {comparison}."
                )

    elif intent == "delivery_success":
        rate = metrics.get("delivery_success_percentage")
        if rate is not None:
            findings.append(
                f"Delivery success rate is {rate:.2f}%."
            )
            findings.append(
                f"{metrics.get('delivered_orders', 0):,} delivered "
                f"orders out of "
                f"{metrics.get('total_shipments', 0):,} shipments."
            )

    else:
        revenue = metrics.get("total_revenue")
        orders = metrics.get("total_orders")

        if revenue is not None:
            findings.append(
                f"Total revenue is {revenue:,.2f}."
            )

        if orders is not None:
            findings.append(
                f"Total distinct orders: {orders:,}."
            )

    if not findings:
        findings.append(
            "No matching metrics were available for this question."
        )

    return {"findings": findings}

# Node 6: Generate the final report



def generate_report(state: BusinessState) -> dict:
    """Generate a concise business investigation report."""
    import json
    import os

    print("REPORT NODE STARTED")

    question = state.get("question", "")
    intent = state.get("intent", "general")
    metrics = state.get("analysis", {})
    findings = state.get("findings", [])
    report_focus = metrics.get("report_focus", "overall")

    print("REPORT ANALYSIS:", metrics)
    print("REPORT FINDINGS:", findings)

    # Handle calculation errors first.
    if metrics.get("error"):
        return {
            "final_report": (
                "# Business Investigation Report\n\n"
                f"**Question:** {question}\n\n"
                f"**Issue:** {metrics['error']}"
            )
        }

    # Special report: salesperson monthly revenue.
    if intent == "salesperson_monthly":
        monthly = metrics.get("monthly_revenue", {})
        salesperson = metrics.get("salesperson", "Unknown")
        total = metrics.get("total_revenue", 0)

        report_lines = [
            f"# Monthly Revenue Report: {salesperson}",
            "",
            f"**Total revenue:** {total:,.2f}",
            "",
            "## Month-by-Month Revenue",
            "",
            "| Month | Revenue |",
            "|---|---:|",
        ]

        for month, revenue in monthly.items():
            report_lines.append(f"| {month} | {revenue:,.2f} |")

        report_lines.extend([
            "",
            f"**Highest revenue month:** "
            f"{metrics.get('highest_month', 'N/A')} "
            f"({metrics.get('highest_month_revenue', 0):,.2f})",
            "",
            f"**Lowest revenue month:** "
            f"{metrics.get('lowest_month', 'N/A')} "
            f"({metrics.get('lowest_month_revenue', 0):,.2f})",
        ])

        return {"final_report": "\n".join(report_lines)}

    # Prepare the data for the LLM.
    context = f"""
User question:
{question}

Detected intent:
{intent}

Report focus:
{report_focus}

Calculated metrics:
{json.dumps(metrics, indent=2, default=str)}

Findings:
{json.dumps(findings, indent=2, default=str)}
"""

    system_prompt = """
You are an AI Business Investigation Assistant
for a chocolate sales and shipment business.

Generate a concise, accurate report using only the supplied data.

Rules:
1. Start with a meaningful Markdown title.
2. Give the direct answer near the beginning.
3. Use only supplied metrics and findings.
4. Never invent numbers, causes, trends, or facts.
5. Do not repeat information.
6. Use simple business language.
7. Describe comparisons objectively.
8. Do not claim correlation proves causation.
9. Mention limitations when the data cannot fully answer the question.
10. Return only the report.

Shipment rules:
- The delivered percentage is the current share marked Delivered.
- In Transit, Processing, and Out for Delivery are not necessarily failures.
- Do not describe the current delivered share as the final delivery success rate.
- For combined carrier-priority analysis, use only combined_breakdown.
- If combined results are missing, explain that the comparison could not be calculated.

Use Markdown tables when they make comparisons easier.
"""

    try:
        token = os.getenv("HUGGINGFACEHUB_API_TOKEN")

        if not token:
            raise ValueError(
                "HUGGINGFACEHUB_API_TOKEN is missing. "
                "Check your .env file."
            )

        llm = HuggingFaceEndpoint(
            repo_id="XiaomiMiMo/MiMo-V2.6-Pro-RL",
            task="text-generation",
            max_new_tokens=512,
            temperature=0.3,
            huggingfacehub_api_token=token,
        )

        chat_model = ChatHuggingFace(llm=llm)

        response = chat_model.invoke([
            ("system", system_prompt),
            ("human", context),
        ])

        report = response.content

        if isinstance(report, list):
            report = "\n".join(
                str(part.get("text", part))
                if isinstance(part, dict)
                else str(part)
                for part in report
            )

        report = str(report).strip()

        if not report:
            raise ValueError("The model returned an empty report.")

        print("DEBUG: Report generated successfully.")
        return {"final_report": report}

    except Exception as error:
        print(f"Hugging Face LLM error: {error}")
        print("DEBUG: Generating fallback report.")

        report_lines = [
            "# Business Investigation Report",
            "",
            f"**Question:** {question}",
            "",
        ]

        # Salesperson ranking fallback.
        if intent == "top_salesperson":
            ranking = metrics.get("ranking", {})

            if ranking:
                sorted_people = sorted(
                    ranking.items(),
                    key=lambda item: item[1],
                    reverse=True,
                )

                report_lines.extend([
                    "## Salesperson Revenue Ranking",
                    "",
                    "| Rank | Salesperson | Revenue |",
                    "|---:|---|---:|",
                ])

                for rank, (name, revenue) in enumerate(
                    sorted_people[:5], start=1
                ):
                    report_lines.append(
                        f"| {rank} | {name} | {revenue:,.2f} |"
                    )

                top_name, top_revenue = sorted_people[0]
                report_lines.extend([
                    "",
                    f"**Highest revenue:** {top_name} "
                    f"({top_revenue:,.2f})",
                ])
            else:
                report_lines.append(
                    "No salesperson revenue ranking is available."
                )

        # Top product or country fallback.
        elif intent in ["top_product", "top_country"]:
            item = metrics.get("top_item")
            revenue = metrics.get("top_item_revenue")
            ranking = metrics.get("ranking", {})
            label = "Product" if intent == "top_product" else "Country"

            if item is not None and revenue is not None:
                report_lines.extend([
                    f"## Revenue by {label}",
                    "",
                    f"**Highest revenue {label.lower()}:** "
                    f"{item} ({revenue:,.2f})",
                ])

            if ranking:
                report_lines.extend([
                    "",
                    f"| {label} | Revenue |",
                    "|---|---:|",
                ])

                for name, value in list(ranking.items())[:5]:
                    report_lines.append(f"| {name} | {value:,.2f} |")

        # Delivery and shipment fallback.
        elif intent == "delivery_success":
            delivered = metrics.get("delivered_orders")
            total = metrics.get("total_shipments")
            rate = metrics.get("delivery_success_percentage")

            if delivered is not None and total is not None:
                report_lines.extend([
                    "## Current Delivery Overview",
                    "",
                    f"**{delivered:,} of {total:,} shipments "
                    f"({rate:.2f}%) are currently marked as delivered.**",
                    "",
                ])

            if report_focus == "combined_carrier_priority":
                breakdown = metrics.get("combined_breakdown", {})
                heading = "Carrier Comparison for Selected Priority"
            elif report_focus == "carrier":
                breakdown = metrics.get("carrier_breakdown", {})
                heading = "Carrier Comparison"
            elif report_focus == "priority":
                breakdown = metrics.get("priority_breakdown", {})
                heading = "Priority Comparison"
            elif report_focus == "damage_risk":
                breakdown = metrics.get("damage_risk_breakdown", {})
                heading = "Damage-Risk Comparison"
            else:
                breakdown = metrics.get("status_breakdown", {})
                heading = "Shipment Status Breakdown"

            if breakdown:
                report_lines.extend([
                    f"## {heading}",
                    "",
                ])

                if report_focus == "overall":
                    report_lines.extend([
                        "| Status | Shipments |",
                        "|---|---:|",
                    ])

                    for name, count in breakdown.items():
                        report_lines.append(
                            f"| {name} | {count:,} |"
                        )
                else:
                    report_lines.extend([
                        "| Category | Delivered | Total | "
                        "Current delivered share |",
                        "|---|---:|---:|---:|",
                    ])

                    for name, values in breakdown.items():
                        report_lines.append(
                            f"| {name} "
                            f"| {values.get('delivered_orders', 0):,} "
                            f"| {values.get('total_orders', 0):,} "
                            f"| {values.get('success_rate', 0):.2f}% |"
                        )
            else:
                report_lines.append(
                    "The requested shipment comparison could not be calculated."
                )

            report_lines.extend([
                "",
                "**Limitation:** These figures reflect current shipment "
                "statuses. Shipments still in progress are not necessarily "
                "failed deliveries.",
            ])

        # Other intents: use the findings generated by the previous node.
        elif findings:
            report_lines.extend([
                "## Key Findings",
                "",
            ])
            report_lines.extend(f"- {item}" for item in findings)

        # Last resort: display available metrics.
        elif metrics:
            report_lines.extend([
                "## Calculated Metrics",
                "",
                "```json",
                json.dumps(metrics, indent=2, default=str),
                "```",
            ])
        else:
            report_lines.append(
                "No calculated findings or metrics are available."
            )

        return {"final_report": "\n".join(report_lines)}
