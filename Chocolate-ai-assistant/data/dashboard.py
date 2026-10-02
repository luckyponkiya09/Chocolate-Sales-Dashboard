
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LLM_PROJECT_PATH = PROJECT_ROOT / "LLM"

sys.path.insert(0, str(LLM_PROJECT_PATH))

from app.graph import run_investigation
import app.graph
st.write("Imported graph file:", app.graph.__file__)

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Chocolate Business Intelligence",
    page_icon="🍫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------
# CUSTOM STYLING
# --------------------------------------------------

st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    [data-testid="stSidebar"] {
        background-color: #171923;
    }
    div[data-testid="stMetric"] {
        background-color: #20232e;
        border: 1px solid #303442;
        padding: 16px;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# LOAD AND CLEAN DATA
# --------------------------------------------------

@st.cache_data
def load_data():
    base_dir = Path(__file__).parent
    data_path = base_dir / "Chocolate main Data.xlsx"

    data = pd.read_excel(data_path)

    # Clean column names
    data.columns = (
        data.columns
        .str.strip()
        .str.replace(r"\s+", " ", regex=True)
    )

    # Standardize common spelling variations
    data = data.rename(columns={
        "Dilevery Cost": "Delivery Cost",
        "Delivery cost": "Delivery Cost"
    })

    # Remove exact duplicate records
    original_rows = len(data)
    duplicate_count = int(data.duplicated().sum())
    data = data.drop_duplicates().copy()

    # Convert date column
    data["Date"] = pd.to_datetime(
        data["Date"],
        errors="coerce"
    )

    # Convert numeric columns
    numeric_columns = [
        "Amount",
        "Boxes Shipped",
        "Delivery Cost",
        "Quantity Sold",
        "Total Sales",
        "Order_ID"
    ]

    for col in numeric_columns:
        if col in data.columns:
            data[col] = pd.to_numeric(
                data[col],
                errors="coerce"
            )

    # Clean text columns
    text_columns = [
        "Sales Person",
        "Country",
        "Product"
    ]

    for col in text_columns:
        if col in data.columns:
            data[col] = data[col].astype("string").str.strip()

    return data, original_rows, duplicate_count


try:
    df, original_rows, duplicate_count = load_data()

except FileNotFoundError:
    st.error(
        "Dataset not found. Make sure "
        "'Chocolate main Data.xlsx' is in the same folder as app.py."
    )
    st.stop()

except Exception as e:
    st.error(f"Error loading dataset: {e}")
    st.stop()


# Required columns
required_columns = [
    "Order_ID",
    "Sales Person",
    "Country",
    "Product",
    "Date",
    "Boxes Shipped",
    "Delivery Cost",
    "Quantity Sold",
    "Total Sales"
]

missing_columns = [
    col for col in required_columns
    if col not in df.columns
]

if missing_columns:
    st.error(
        f"Missing required columns: {', '.join(missing_columns)}"
    )
    st.write("Available columns:", df.columns.tolist())
    st.stop()

# --------------------------------------------------
# SIDEBAR NAVIGATION
# --------------------------------------------------

st.sidebar.title("🍫 Chocolate BI")
st.sidebar.caption("Business Intelligence Dashboard")

st.sidebar.markdown("---")

page = st.sidebar.radio(
    "Navigation",
    [
        "Overview",
        "Product Analysis",
        "Country Analysis",
        "Salesperson Analysis",
        "Logistics Analysis",
        "AI Assistant"
    ],
    index=0
)

st.sidebar.markdown("---")

# --------------------------------------------------
# GLOBAL FILTERS
# --------------------------------------------------

st.sidebar.subheader("Dashboard Filters")

countries = sorted(
    df["Country"].dropna().unique().tolist()
)

products = sorted(
    df["Product"].dropna().unique().tolist()
)

salespersons = sorted(
    df["Sales Person"].dropna().unique().tolist()
)

def checkbox_dropdown(label, options, key_prefix):
    """Power BI-style multi-select dropdown using a Streamlit popover."""
    state_key = f"{key_prefix}_selected"

    # Start with all options selected, matching the old slicer behavior.
    if state_key not in st.session_state:
        st.session_state[state_key] = list(options)

    # Remove values that no longer exist in the available options.
    st.session_state[state_key] = [
        value for value in st.session_state[state_key]
        if value in options
    ]

    selected = st.session_state[state_key]
    summary = "All selected" if len(selected) == len(options) else (
        "None selected" if not selected else f"{len(selected)} selected"
    )

    with st.sidebar.popover(f"{label}: {summary}", use_container_width=True):
        col_all, col_clear = st.columns(2)

        if col_all.button("Select all", key=f"{key_prefix}_select_all", use_container_width=True):
            st.session_state[state_key] = list(options)
            for index in range(len(options)):
                st.session_state[f"{key_prefix}_option_{index}"] = True
            st.rerun()

        if col_clear.button("Clear", key=f"{key_prefix}_clear", use_container_width=True):
            st.session_state[state_key] = []
            for index in range(len(options)):
                st.session_state[f"{key_prefix}_option_{index}"] = False
            st.rerun()

        st.caption("Choose one or more values")
        for index, option in enumerate(options):
            st.checkbox(
                str(option),
                value=option in st.session_state[state_key],
                key=f"{key_prefix}_option_{index}"
            )

        # Read checkbox values after rendering and persist them for filtering.
        st.session_state[state_key] = [
            option for index, option in enumerate(options)
            if st.session_state.get(f"{key_prefix}_option_{index}", False)
        ]

    return st.session_state[state_key]


selected_countries = checkbox_dropdown(
    "Select Country", countries, "country_filter"
)

selected_products = checkbox_dropdown(
    "Select Product", products, "product_filter"
)

selected_salespersons = checkbox_dropdown(
    "Select Salesperson", salespersons, "salesperson_filter"
)

valid_dates = df["Date"].dropna()

if valid_dates.empty:
    st.error("No valid dates were found in the dataset.")
    st.stop()

min_date = valid_dates.min().date()
max_date = valid_dates.max().date()

selected_dates = st.sidebar.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
    key="date_filter"
)

# Apply all filters
filtered_df = df.copy()

if selected_countries:
    filtered_df = filtered_df[
        filtered_df["Country"].isin(selected_countries)
    ]
else:
    filtered_df = filtered_df.iloc[0:0]

if selected_products:
    filtered_df = filtered_df[
        filtered_df["Product"].isin(selected_products)
    ]
else:
    filtered_df = filtered_df.iloc[0:0]

if selected_salespersons:
    filtered_df = filtered_df[
        filtered_df["Sales Person"].isin(selected_salespersons)
    ]
else:
    filtered_df = filtered_df.iloc[0:0]

if isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 2:
    start_date, end_date = selected_dates

    filtered_df = filtered_df[
        filtered_df["Date"].dt.date.between(
            start_date,
            end_date
        )
    ]

elif isinstance(selected_dates, (tuple, list)) and len(selected_dates) == 1:
    selected_date = selected_dates[0]

    filtered_df = filtered_df[
        filtered_df["Date"].dt.date == selected_date
    ]

# --------------------------------------------------
# COMMON FUNCTIONS
# --------------------------------------------------

def format_currency(value):
    return f"${value:,.0f}"


def show_kpis(data):
    revenue = data["Total Sales"].sum()
    orders = data["Order_ID"].nunique()
    boxes = data["Boxes Shipped"].sum()
    quantity = data["Quantity Sold"].sum()

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Revenue",
        format_currency(revenue)
    )

    col2.metric(
        "Total Orders",
        f"{orders:,.0f}"
    )

    col3.metric(
        "Boxes Shipped",
        f"{boxes:,.0f}"
    )

    col4.metric(
        "Quantity Sold",
        f"{quantity:,.0f}"
    )


def show_chart(fig, height=450):
    fig.update_layout(
        template="plotly_dark",
        height=height,
        margin=dict(l=20, r=20, t=50, b=40),
        legend_title_text=""
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


def show_empty_message():
    st.warning(
        "No data is available for the selected filters. "
        "Please change your filters."
    )


def show_dataset(data):
    with st.expander("View Filtered Dataset"):
        st.write(f"Showing {len(data):,} rows.")
        st.dataframe(
            data,
            use_container_width=True,
            hide_index=True
        )

        csv = data.to_csv(index=False).encode("utf-8")

        st.download_button(
            "Download Filtered Data as CSV",
            data=csv,
            file_name="chocolate_filtered_data.csv",
            mime="text/csv"
        )


# --------------------------------------------------
# COMMON HEADER
# --------------------------------------------------

st.title("🍫 Chocolate Business Intelligence")
st.caption("Interactive Chocolate Sales Dashboard")

st.markdown("---")

# --------------------------------------------------
# PAGE 1: OVERVIEW
# --------------------------------------------------

if page == "Overview":

    st.header("Business Overview")

    # Data quality summary
    st.subheader("Data Quality Summary")

    col1, col2, col3 = st.columns(3)

    col1.metric(
        "Original Rows",
        f"{original_rows:,}"
    )

    col2.metric(
        "Duplicates Removed",
        f"{duplicate_count:,}"
    )

    col3.metric(
        "Clean Rows",
        f"{len(df):,}"
    )

    st.markdown("---")

    # Main KPIs
    st.subheader("Key Performance Indicators")

    if filtered_df.empty:
        show_empty_message()
    else:
        show_kpis(filtered_df)

        st.markdown("---")

        # Monthly revenue
        st.subheader("Monthly Revenue Trends")

        monthly = (
            filtered_df
            .dropna(subset=["Date"])
            .assign(
                Month=lambda x: x["Date"].dt.to_period("M").dt.to_timestamp()
            )
            .groupby("Month", as_index=False)["Total Sales"]
            .sum()
            .sort_values("Month")
        )

        if not monthly.empty:
            fig = px.line(
                monthly,
                x="Month",
                y="Total Sales",
                markers=True,
                title="Monthly Revenue",
                labels={
                    "Month": "Month",
                    "Total Sales": "Revenue ($)"
                }
            )

            show_chart(fig)

        # Country and product overview
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Revenue by Country")

            country_data = (
                filtered_df
                .groupby("Country", as_index=False)["Total Sales"]
                .sum()
                .sort_values("Total Sales", ascending=False)
            )

            fig = px.bar(
                country_data,
                x="Country",
                y="Total Sales",
                title="Revenue by Country",
                color="Country",
                labels={"Total Sales": "Revenue ($)"}
            )

            show_chart(fig, height=400)

        with col2:
            st.subheader("Revenue by Product")

            product_data = (
                filtered_df
                .groupby("Product", as_index=False)["Total Sales"]
                .sum()
                .sort_values("Total Sales", ascending=False)
            )

            fig = px.bar(
                product_data,
                x="Total Sales",
                y="Product",
                orientation="h",
                title="Revenue by Product",
                labels={"Total Sales": "Revenue ($)"}
            )

            fig.update_layout(
                yaxis={"categoryorder": "total ascending"}
            )

            show_chart(fig, height=400)

    show_dataset(filtered_df)


# --------------------------------------------------
# PAGE 2: PRODUCT ANALYSIS
# --------------------------------------------------

elif page == "Product Analysis":

    st.header("Product Analysis")

    if filtered_df.empty:
        show_empty_message()

    else:
        show_kpis(filtered_df)

        st.markdown("---")

        # Revenue by product
        st.subheader("Revenue by Product")

        product_revenue = (
            filtered_df
            .groupby("Product", as_index=False)
            .agg(
                Revenue=("Total Sales", "sum"),
                Quantity=("Quantity Sold", "sum"),
                Boxes=("Boxes Shipped", "sum"),
                Orders=("Order_ID", "nunique")
            )
            .sort_values("Revenue", ascending=False)
        )

        fig = px.bar(
            product_revenue,
            x="Product",
            y="Revenue",
            color="Product",
            title="Total Revenue by Product",
            hover_data=[
                "Quantity",
                "Boxes",
                "Orders"
            ],
            labels={"Revenue": "Revenue ($)"}
        )

        fig.update_xaxes(tickangle=-45)

        show_chart(fig, height=550)

        # Product quantity and revenue comparison
        st.subheader("Product Sales Comparison")

        fig = px.scatter(
            product_revenue,
            x="Quantity",
            y="Revenue",
            size="Boxes",
            color="Product",
            hover_name="Product",
            title="Revenue vs Quantity Sold",
            labels={
                "Quantity": "Quantity Sold",
                "Revenue": "Revenue ($)"
            }
        )

        show_chart(fig, height=500)

        # Product table
        st.subheader("Product Performance Table")

        st.dataframe(
            product_revenue,
            use_container_width=True,
            hide_index=True
        )

    show_dataset(filtered_df)


# --------------------------------------------------
# PAGE 3: COUNTRY ANALYSIS
# --------------------------------------------------

elif page == "Country Analysis":

    st.header("Country Analysis")

    if filtered_df.empty:
        show_empty_message()

    else:
        show_kpis(filtered_df)

        st.markdown("---")

        # Revenue by country
        st.subheader("Revenue by Country")

        country_revenue = (
            filtered_df
            .groupby("Country", as_index=False)
            .agg(
                Revenue=("Total Sales", "sum"),
                Quantity=("Quantity Sold", "sum"),
                Boxes=("Boxes Shipped", "sum"),
                Orders=("Order_ID", "nunique")
            )
            .sort_values("Revenue", ascending=False)
        )

        fig = px.bar(
            country_revenue,
            x="Country",
            y="Revenue",
            color="Country",
            title="Country-wise Revenue",
            hover_data=[
                "Quantity",
                "Boxes",
                "Orders"
            ],
            labels={"Revenue": "Revenue ($)"}
        )

        show_chart(fig)

        # Product revenue by country
        st.subheader("Product Revenue Across Countries")

        regional_data = (
            filtered_df
            .groupby(
                ["Product", "Country"],
                as_index=False
            )["Total Sales"]
            .sum()
        )

        fig = px.bar(
            regional_data,
            x="Product",
            y="Total Sales",
            color="Country",
            barmode="group",
            title="Product Revenue Across Countries",
            labels={"Total Sales": "Revenue ($)"}
        )

        fig.update_xaxes(tickangle=-45)

        show_chart(fig, height=600)

        # Country comparison table
        st.subheader("Country Performance Table")

        st.dataframe(
            country_revenue,
            use_container_width=True,
            hide_index=True
        )

    show_dataset(filtered_df)


# --------------------------------------------------
# PAGE 4: SALESPERSON ANALYSIS
# --------------------------------------------------

elif page == "Salesperson Analysis":

    st.header("Salesperson Analysis")

    if filtered_df.empty:
        show_empty_message()

    else:
        show_kpis(filtered_df)

        st.markdown("---")

        # Salesperson performance
        st.subheader("Salesperson Revenue")

        salesperson_data = (
            filtered_df
            .groupby("Sales Person", as_index=False)
            .agg(
                Revenue=("Total Sales", "sum"),
                Orders=("Order_ID", "nunique"),
                Quantity=("Quantity Sold", "sum"),
                Boxes=("Boxes Shipped", "sum")
            )
            .sort_values("Revenue", ascending=False)
        )

        fig = px.bar(
            salesperson_data,
            x="Sales Person",
            y="Revenue",
            color="Revenue",
            title="Revenue by Salesperson",
            hover_data=[
                "Orders",
                "Quantity",
                "Boxes"
            ],
            labels={"Revenue": "Revenue ($)"}
        )

        fig.update_xaxes(tickangle=-45)

        show_chart(fig, height=550)

        # Orders comparison
        st.subheader("Orders by Salesperson")

        fig = px.bar(
            salesperson_data.sort_values(
                "Orders",
                ascending=False
            ),
            x="Sales Person",
            y="Orders",
            color="Orders",
            title="Total Orders by Salesperson",
            labels={"Orders": "Number of Orders"}
        )

        fig.update_xaxes(tickangle=-45)

        show_chart(fig, height=500)

        # Performance table
        st.subheader("Salesperson Performance Table")

        st.dataframe(
            salesperson_data,
            use_container_width=True,
            hide_index=True
        )

    show_dataset(filtered_df)


# --------------------------------------------------
# PAGE 5: LOGISTICS ANALYSIS
# --------------------------------------------------

elif page == "Logistics Analysis":

    st.header("Logistics Analysis")

    if filtered_df.empty:
        show_empty_message()

    else:
        # Logistics KPIs
        total_boxes = filtered_df["Boxes Shipped"].sum()
        total_quantity = filtered_df["Quantity Sold"].sum()
        total_delivery_cost = filtered_df["Delivery Cost"].sum()

        cost_per_box = (
            total_delivery_cost / total_boxes
            if total_boxes > 0
            else 0
        )

        col1, col2, col3, col4 = st.columns(4)

        col1.metric(
            "Boxes Shipped",
            f"{total_boxes:,.0f}"
        )

        col2.metric(
            "Quantity Sold",
            f"{total_quantity:,.0f}"
        )

        col3.metric(
            "Total Delivery Cost",
            format_currency(total_delivery_cost)
        )

        col4.metric(
            "Delivery Cost per Box",
            f"${cost_per_box:,.2f}"
        )

        st.markdown("---")

        # Delivery cost by country
        st.subheader("Delivery Cost by Country")

        delivery_country = (
            filtered_df
            .groupby("Country", as_index=False)
            .agg(
                Delivery_Cost=("Delivery Cost", "sum"),
                Boxes=("Boxes Shipped", "sum")
            )
        )

        fig = px.bar(
            delivery_country,
            x="Country",
            y="Delivery_Cost",
            color="Country",
            title="Delivery Cost by Country",
            hover_data=["Boxes"],
            labels={
                "Delivery_Cost": "Delivery Cost ($)"
            }
        )

        show_chart(fig)

        # Shipping volume by product
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Boxes Shipped by Product")

            boxes_product = (
                filtered_df
                .groupby("Product", as_index=False)["Boxes Shipped"]
                .sum()
                .sort_values("Boxes Shipped", ascending=False)
            )

            fig = px.bar(
                boxes_product,
                x="Boxes Shipped",
                y="Product",
                orientation="h",
                title="Boxes Shipped by Product",
                labels={
                    "Boxes Shipped": "Boxes"
                }
            )

            fig.update_layout(
                yaxis={"categoryorder": "total ascending"}
            )

            show_chart(fig, height=500)

        with col2:
            st.subheader("Quantity Sold by Product")

            quantity_product = (
                filtered_df
                .groupby("Product", as_index=False)["Quantity Sold"]
                .sum()
                .sort_values("Quantity Sold", ascending=False)
            )

            fig = px.bar(
                quantity_product,
                x="Quantity Sold",
                y="Product",
                orientation="h",
                title="Quantity Sold by Product",
                labels={
                    "Quantity Sold": "Quantity"
                }
            )

            fig.update_layout(
                yaxis={"categoryorder": "total ascending"}
            )

            show_chart(fig, height=500)

        # Logistics table
        st.subheader("Logistics Performance by Country")

        st.dataframe(
            delivery_country,
            use_container_width=True,
            hide_index=True
        )

    show_dataset(filtered_df)


# --------------------------------------------------
# PAGE 6: AI BUSINESS ASSISTANT (UI FOUNDATION)
# --------------------------------------------------

elif page == "AI Assistant":

    st.header("🤖 AI Business Assistant")
    st.caption(
        "Ask questions about your chocolate sales data. "
        "The AI connection will be added in the next step."
    )

    st.markdown("---")

    st.subheader("Ask a business question")

    example_questions = [
        "Which product has the highest revenue?",
        "Compare sales across countries.",
        "Who are the top 5 salespeople?",
        "How did monthly revenue change?",
        "What is the total delivery cost?"
    ]

    selected_example = st.selectbox(
        "Try an example question",
        ["Choose an example..."] + example_questions,
        key="ai_example_question"
    )

    if selected_example != "Choose an example...":
        st.session_state["ai_question"] = selected_example

    with st.form("ai_question_form", clear_on_submit=False):
        question = st.text_area(
            "Your question",
            key="ai_question",
            placeholder="For example: Which product generated the most revenue?",
            height=110
        )
        submitted = st.form_submit_button(
            "Ask",
            type="primary",
            use_container_width=True
        )

    
    st.subheader("Answer")

    # if submitted:
    #     if not question.strip():
    #         st.warning("Please enter a business question.")
    #     else:
    #         with st.spinner("Analyzing your business question..."):
    #             try:
    #                 result = run_investigation(question.strip())

    #                 report = result.get("final_report")

    #                 if report and str(report).strip():
    #                     st.success("Investigation completed!")
    #                     st.markdown(report)
    #                 else:
    #                     st.warning(
    #                         "The workflow completed, but no report was returned."
    #                     )

    #                     with st.expander("Debug information"):
    #                         st.write("Intent:", result.get("intent"))
    #                         st.write("Analysis:", result.get("analysis"))
    #                         st.write("Findings:", result.get("findings"))

    #             except Exception as error:
    #                 st.error(f"An error occurred: {error}")
    if submitted:
        if not question.strip():
            st.warning("Please enter a question.")
        else:
            try:
                st.write("Question sent:", repr(question.strip()))

                with st.spinner("Running LangGraph..."):
                    result = run_investigation(question.strip())

                st.write("Detected intent:", result.get("intent"))
                st.write("Report focus:", result.get("report_focus"))

                with st.expander("Debug: Full workflow result"):
                    st.json({
                        key: str(value)
                        for key, value in result.items()
                    })

                report = result.get("final_report")

                if report:
                    st.markdown(report)
                else:
                    st.warning("No final report returned.")

            except Exception as error:
                st.exception(error)
    else:
        st.caption(
            "Your answer and supporting figures or charts "
            "will appear here after you ask a question."
        )


    st.markdown("---")
    st.subheader("Current data context")
    st.write(
        f"**Rows available:** {len(filtered_df):,} "
        "(based on the dashboard filters)"
    )
    st.caption(
        "In the next step, the assistant will use these filtered records "
        "to answer questions in the context of the current dashboard selection."
    )


# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.markdown("---")

st.caption(
    "Chocolate Business Intelligence Dashboard | "
    "Built with Streamlit, Pandas and Plotly"
)