from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


st.set_page_config(
    page_title="E-commerce Store Insights",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_PATH = Path(__file__).with_name("ecommerce_sales_customer_analytics_150k.csv")
REQUIRED_COLUMNS = {
    "order_id",
    "order_date",
    "order_status",
    "sales_channel",
    "customer_id",
    "customer_segment",
    "customer_country",
    "region",
    "payment_method",
    "payment_status",
    "currency",
    "shipping_method",
    "delivery_days",
    "delivery_status",
    "customer_rating",
    "marketing_channel",
    "quantity",
    "discount_amount",
    "net_sales",
    "profit",
    "profit_margin_percentage",
    "is_repeat_customer",
}
CURRENCY_MARKS = {
    "USD": "$",
    "GBP": "£",
    "EUR": "€",
    "CAD": "CA$",
    "AUD": "A$",
    "INR": "₹",
    "AED": "AED ",
}
COLORS = ["#4F46E5", "#14B8A6", "#F59E0B", "#EC4899", "#64748B", "#8B5CF6"]


@st.cache_data(show_spinner="Reading the sales data...")
def load_data(contents: bytes) -> pd.DataFrame:
    data = pd.read_csv(BytesIO(contents), encoding="utf-8-sig")
    missing_columns = REQUIRED_COLUMNS.difference(data.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"The CSV is missing required columns: {missing}")

    data["order_date"] = pd.to_datetime(data["order_date"], errors="coerce")
    data["invalid_order_date"] = data["order_date"].isna()
    data = data.loc[~data["invalid_order_date"]].copy()
    numeric_columns = (
        "delivery_days",
        "customer_rating",
        "quantity",
        "discount_amount",
        "net_sales",
        "profit",
        "profit_margin_percentage",
    )
    for column in numeric_columns:
        original = data[column]
        data[column] = pd.to_numeric(data[column], errors="coerce")
        invalid_values = int((original.notna() & data[column].isna()).sum())
        if invalid_values:
            raise ValueError(
                f"Column '{column}' contains {invalid_values:,} non-numeric value(s)."
            )

    return data


def money(value: float, currency: str) -> str:
    symbol = CURRENCY_MARKS.get(currency, f"{currency} ")
    return f"{symbol}{value:,.2f}"


def multiselect_filter(label: str, values: pd.Series) -> list[str]:
    options = sorted(values.dropna().astype(str).unique().tolist())
    return st.multiselect(label, options, default=options)


def style_chart(fig: go.Figure, height: int = 360) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=12, r=12, t=30, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#344054", family="Inter, sans-serif"),
        legend_title_text="",
        hoverlabel=dict(bgcolor="white"),
    )
    fig.update_xaxes(showgrid=False, linecolor="#E4E7EC")
    fig.update_yaxes(gridcolor="#EAECF0", zerolinecolor="#EAECF0")
    return fig


st.markdown(
    """
    <style>
    .stApp { background: #F7F8FC; }
    [data-testid="stSidebar"] { background: #FFFFFF; }
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; }
    .hero {
        padding: 1.35rem 1.55rem;
        margin-bottom: 1.1rem;
        border-radius: 18px;
        background: linear-gradient(115deg, #18224A 0%, #4338CA 65%, #6366F1 100%);
        color: white;
    }
    .hero h1 { margin: 0 0 .25rem 0; font-size: 2rem; }
    .hero p { margin: 0; color: #E0E7FF; }
    [data-testid="stMetric"] {
        background: white; border: 1px solid #EAECF0; padding: 1rem;
        border-radius: 14px; box-shadow: 0 2px 6px rgba(16, 24, 40, .04);
    }
    [data-testid="stMetricLabel"] { color: #667085; }
    div[data-testid="stPlotlyChart"] {
        background: white; border: 1px solid #EAECF0; border-radius: 14px;
        padding: .3rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero">
      <h1>🛍️ E-commerce Store Insights</h1>
      <p>Explore sales performance, customer behavior, marketing, and delivery trends.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

uploaded_file = st.sidebar.file_uploader(
    "Replace the default data",
    type=["csv"],
    help="Upload a CSV with the same e-commerce columns to explore another extract.",
)

if uploaded_file is not None:
    source_bytes = uploaded_file.getvalue()
    source_name = uploaded_file.name
elif DATA_PATH.exists():
    source_bytes = DATA_PATH.read_bytes()
    source_name = DATA_PATH.name
else:
    st.error(
        "The default dataset is missing. Place "
        "`ecommerce_sales_customer_analytics_150k.csv` beside `app.py` or upload a CSV."
    )
    st.stop()

try:
    raw_data = load_data(source_bytes)
except (ValueError, pd.errors.ParserError, UnicodeDecodeError) as error:
    st.error(f"Could not load {source_name}: {error}")
    st.stop()

invalid_dates = int(raw_data["invalid_order_date"].sum())
raw_data = raw_data.drop(columns="invalid_order_date")
if invalid_dates:
    st.warning(f"{invalid_dates:,} row(s) with invalid order dates were excluded.")

with st.sidebar:
    st.header("Dashboard filters")
    st.caption(f"Data source: **{source_name}** · {len(raw_data):,} valid dated rows")

    min_date = raw_data["order_date"].min().date()
    max_date = raw_data["order_date"].max().date()
    selected_dates = st.date_input(
        "Order date range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    currency_options = sorted(raw_data["currency"].dropna().unique().tolist())
    selected_currency = st.selectbox(
        "Reporting currency",
        currency_options,
        index=currency_options.index("USD") if "USD" in currency_options else 0,
        help="Amounts are not converted. Choose one currency to keep totals comparable.",
    )
    selected_regions = multiselect_filter("Region", raw_data["region"])
    selected_countries = multiselect_filter("Country", raw_data["customer_country"])
    selected_channels = multiselect_filter("Sales channel", raw_data["sales_channel"])
    selected_statuses = multiselect_filter("Order status", raw_data["order_status"])
    selected_segments = multiselect_filter("Customer segment", raw_data["customer_segment"])

if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
    start_date, end_date = selected_dates
else:
    start_date = end_date = selected_dates

filtered = raw_data.loc[
    raw_data["order_date"].dt.date.between(start_date, end_date)
    & raw_data["currency"].eq(selected_currency)
    & raw_data["region"].isin(selected_regions)
    & raw_data["customer_country"].isin(selected_countries)
    & raw_data["sales_channel"].isin(selected_channels)
    & raw_data["order_status"].isin(selected_statuses)
    & raw_data["customer_segment"].isin(selected_segments)
].copy()

if filtered.empty:
    st.info("No records match these filters. Expand the date range or select more filter values.")
    st.stop()

orders_count = filtered["order_id"].nunique()
sales_total = filtered["net_sales"].sum()
profit_total = filtered["profit"].sum()
profit_margin = profit_total / sales_total * 100 if sales_total else 0
average_order_value = sales_total / orders_count if orders_count else 0
repeat_customer_share = filtered.loc[
    filtered["is_repeat_customer"], "customer_id"
].nunique() / max(filtered["customer_id"].nunique(), 1) * 100

st.caption(
    f"Showing **{len(filtered):,}** records · {start_date:%b %d, %Y} – "
    f"{end_date:%b %d, %Y} · amounts shown in {selected_currency}"
)

metric_columns = st.columns(5)
metric_columns[0].metric("Orders", f"{orders_count:,}")
metric_columns[1].metric("Net sales", money(sales_total, selected_currency))
metric_columns[2].metric("Profit", money(profit_total, selected_currency))
metric_columns[3].metric("Profit margin", f"{profit_margin:.1f}%")
metric_columns[4].metric("Repeat customers", f"{repeat_customer_share:.1f}%")

st.markdown("")
performance_tab, customer_tab, delivery_tab, data_tab = st.tabs(
    ["📈 Sales performance", "👥 Customers & marketing", "🚚 Delivery & experience", "📋 Data explorer"]
)

with performance_tab:
    st.subheader("Sales performance")
    period = st.radio(
        "Trend interval",
        ["Month", "Quarter", "Year"],
        horizontal=True,
        key="trend_interval",
    )
    trend = filtered.copy()
    if period == "Month":
        trend["period"] = trend["order_date"].dt.to_period("M").dt.to_timestamp()
        date_format = "%b %Y"
    elif period == "Quarter":
        trend["period"] = trend["order_date"].dt.to_period("Q").dt.to_timestamp()
        date_format = "%b %Y"
    else:
        trend["period"] = trend["order_date"].dt.to_period("Y").dt.to_timestamp()
        date_format = "%Y"
    trend = (
        trend.groupby("period", as_index=False)
        .agg(Net_sales=("net_sales", "sum"), Profit=("profit", "sum"))
        .sort_values("period")
    )

    trend_col, status_col = st.columns([1.7, 1])
    with trend_col:
        trend_fig = px.line(
            trend,
            x="period",
            y=["Net_sales", "Profit"],
            markers=True,
            color_discrete_sequence=COLORS[:2],
            labels={"period": "Order date", "value": selected_currency, "variable": ""},
        )
        trend_fig.update_xaxes(tickformat=date_format)
        trend_fig.update_traces(hovertemplate="%{x|%b %Y}<br>%{y:,.2f}<extra>%{fullData.name}</extra>")
        st.plotly_chart(style_chart(trend_fig, 390), width="stretch")
    with status_col:
        status_data = (
            filtered.groupby("order_status", as_index=False)
            .agg(Orders=("order_id", "nunique"))
            .sort_values("Orders", ascending=False)
        )
        status_fig = px.pie(
            status_data,
            names="order_status",
            values="Orders",
            hole=0.62,
            color_discrete_sequence=COLORS,
        )
        status_fig.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(style_chart(status_fig, 390), width="stretch")

    region_col, channel_col = st.columns(2)
    with region_col:
        region_data = (
            filtered.groupby("region", as_index=False)
            .agg(Net_sales=("net_sales", "sum"), Profit=("profit", "sum"))
            .sort_values("Net_sales", ascending=True)
        )
        region_fig = px.bar(
            region_data,
            x="Net_sales",
            y="region",
            orientation="h",
            color="Profit",
            color_continuous_scale="Teal",
            labels={"Net_sales": f"Net sales ({selected_currency})", "region": "Region"},
        )
        st.plotly_chart(style_chart(region_fig), width="stretch")
    with channel_col:
        channel_data = (
            filtered.groupby("sales_channel", as_index=False)
            .agg(Orders=("order_id", "nunique"), Net_sales=("net_sales", "sum"))
            .sort_values("Net_sales", ascending=False)
        )
        channel_fig = px.bar(
            channel_data,
            x="sales_channel",
            y="Net_sales",
            color="Orders",
            color_continuous_scale="Purples",
            labels={
                "sales_channel": "Sales channel",
                "Net_sales": f"Net sales ({selected_currency})",
            },
        )
        st.plotly_chart(style_chart(channel_fig), width="stretch")

with customer_tab:
    st.subheader("Customers & marketing")
    segment_col, marketing_col = st.columns(2)
    with segment_col:
        segment_data = (
            filtered.groupby("customer_segment", as_index=False)
            .agg(
                Customers=("customer_id", "nunique"),
                Net_sales=("net_sales", "sum"),
            )
            .sort_values("Net_sales", ascending=False)
        )
        segment_fig = px.bar(
            segment_data,
            x="customer_segment",
            y="Net_sales",
            color="Customers",
            color_continuous_scale="Teal",
            labels={
                "customer_segment": "Customer segment",
                "Net_sales": f"Net sales ({selected_currency})",
            },
        )
        st.plotly_chart(style_chart(segment_fig), width="stretch")
    with marketing_col:
        marketing_data = (
            filtered.groupby("marketing_channel", as_index=False)
            .agg(
                Net_sales=("net_sales", "sum"),
                Profit=("profit", "sum"),
                Orders=("order_id", "nunique"),
            )
            .sort_values("Net_sales", ascending=False)
        )
        marketing_fig = px.bar(
            marketing_data,
            x="Net_sales",
            y="marketing_channel",
            orientation="h",
            color="Profit",
            color_continuous_scale="Viridis",
            labels={
                "Net_sales": f"Net sales ({selected_currency})",
                "marketing_channel": "Marketing channel",
            },
        )
        marketing_fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(style_chart(marketing_fig, 430), width="stretch")

    st.markdown("#### Discount and profitability")
    scatter_data = filtered.dropna(subset=["discount_amount", "profit"])
    if len(scatter_data) > 4000:
        scatter_data = scatter_data.sample(4000, random_state=42)
    scatter_fig = px.scatter(
        scatter_data,
        x="discount_amount",
        y="profit",
        color="customer_segment",
        opacity=0.55,
        color_discrete_sequence=COLORS,
        labels={
            "discount_amount": f"Discount ({selected_currency})",
            "profit": f"Profit ({selected_currency})",
        },
        hover_data=["order_status", "sales_channel"],
    )
    scatter_fig.add_hline(y=0, line_dash="dash", line_color="#98A2B3")
    st.plotly_chart(style_chart(scatter_fig, 390), width="stretch")

with delivery_tab:
    st.subheader("Delivery & customer experience")
    completed = filtered.loc[filtered["order_status"].eq("Completed")].copy()
    delivered = completed.loc[
        completed["delivery_status"].isin(["On Time", "Early", "Delayed"])
    ].copy()
    delivery_cols = st.columns(4)
    on_time_rate = (
        delivered["delivery_status"].isin(["On Time", "Early"]).mean() * 100
        if not delivered.empty
        else 0
    )
    avg_delivery = delivered["delivery_days"].mean()
    avg_rating = completed["customer_rating"].mean()
    returned_rate = filtered["order_status"].eq("Returned").mean() * 100
    delivery_cols[0].metric("On-time / early delivery", f"{on_time_rate:.1f}%")
    delivery_cols[1].metric(
        "Avg. delivery time",
        f"{avg_delivery:.1f} days" if pd.notna(avg_delivery) else "N/A",
    )
    delivery_cols[2].metric(
        "Avg. customer rating",
        f"{avg_rating:.2f} / 5" if pd.notna(avg_rating) else "N/A",
    )
    delivery_cols[3].metric("Returned orders", f"{returned_rate:.1f}%")

    delivery_col, payment_col = st.columns(2)
    with delivery_col:
        delivery_data = (
            delivered.groupby("shipping_method", as_index=False)
            .agg(
                Avg_days=("delivery_days", "mean"),
                Orders=("order_id", "nunique"),
            )
            .sort_values("Avg_days")
        )
        delivery_fig = px.bar(
            delivery_data,
            x="shipping_method",
            y="Avg_days",
            color="Avg_days",
            color_continuous_scale="Blues",
            labels={"shipping_method": "Shipping method", "Avg_days": "Average days"},
        )
        st.plotly_chart(style_chart(delivery_fig), width="stretch")
    with payment_col:
        payment_data = (
            filtered.groupby("payment_status", as_index=False)
            .agg(Orders=("order_id", "nunique"))
            .sort_values("Orders", ascending=False)
        )
        payment_fig = px.bar(
            payment_data,
            x="payment_status",
            y="Orders",
            color="payment_status",
            color_discrete_sequence=COLORS,
            labels={"payment_status": "Payment status"},
        )
        st.plotly_chart(style_chart(payment_fig), width="stretch")

    st.caption(
        "Delivery speed and rating use completed orders with available delivery/review data. "
        "Returned-order rate is calculated from the currently filtered orders."
    )

with data_tab:
    st.subheader("Filtered order records")
    st.caption(
        "Customer names, postal codes, and free-text reviews are excluded from this preview and export."
    )
    safe_columns = [
        "order_date",
        "order_status",
        "currency",
        "net_sales",
        "profit",
        "profit_margin_percentage",
        "quantity",
        "customer_segment",
        "customer_country",
        "region",
        "sales_channel",
        "marketing_channel",
        "payment_status",
        "shipping_method",
        "delivery_status",
        "delivery_days",
        "customer_rating",
    ]
    export_data = filtered[safe_columns].sort_values("order_date", ascending=False)
    st.dataframe(
        export_data.head(1000),
        width="stretch",
        hide_index=True,
        height=440,
    )
    st.download_button(
        "Download filtered data (CSV)",
        data=export_data.to_csv(index=False).encode("utf-8"),
        file_name="ecommerce_filtered_orders.csv",
        mime="text/csv",
    )
    if len(export_data) > 1000:
        st.caption("Preview shows the latest 1,000 rows; the download contains all filtered rows.")

st.divider()
st.caption(
    "Data note: financial totals use the selected currency without exchange-rate conversion. "
    "Product-category analysis is unavailable because the source file has no product/category field."
)
