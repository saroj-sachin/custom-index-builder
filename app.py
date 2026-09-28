from pathlib import Path

import streamlit as st

from src.data_loader import DataLoader
from src.validator import DataValidator
from src.weighting import WeightCalculator
from src.index_calculator import IndexCalculator

# Application configuration

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

st.set_page_config(
    page_title="Custom Index Builder",
    page_icon="📈",
    layout="wide",
)

st.title("Custom Index Builder")
st.caption(
    "Custom Equity Price Return Index"
)

# Loading backend objects

loader = DataLoader(DATA_DIR)
validator = DataValidator()
weight_calculator = WeightCalculator()
index_calculator = IndexCalculator()

try:
    universe = loader.load_universe()
    prices = loader.load_prices()

except Exception as exc:
    st.error(f"Could not load project data: {exc}")
    st.stop()

# Sidebar

with st.sidebar:
    st.header("Index Configuration")

    display_options = (
        universe["ticker"]
        + " — "
        + universe["company_name"]
    ).tolist()

    selected_labels = st.multiselect(
        "Select constituents",
        options=display_options,
        default=display_options[:5],
    )

    selected_tickers = [
        label.split(" — ", 1)[0]
        for label in selected_labels
    ]

    weighting_method = st.selectbox(
        "Weighting Method",
        [
            "Equal Weight",
            "Float Market Cap",
        ],
    )

    min_date = prices["date"].min().date()
    max_date = prices["date"].max().date()

    start_date = st.date_input(
        "Start Date",
        value=min_date,
        min_value=min_date,
        max_value=max_date,
    )

    end_date = st.date_input(
        "End Date",
        value=max_date,
        min_value=min_date,
        max_value=max_date,
    )

    base_level = st.number_input(
        "Base Index Level",
        min_value=1.0,
        value=100.0,
        step=10.0,
    )

    generate = st.button(
        "Generate Index",
        type="primary",
        use_container_width=True,
    )

# Raw data quality summary

raw_report = validator.validate(universe, prices)

with st.expander("Source Data Validation", expanded=False):
    if raw_report.errors:
        for error in raw_report.errors:
            st.error(error)
    else:
        st.success("No blocking structural data errors found.")

    for warning in raw_report.warnings:
        st.warning(warning)

    c1, c2, c3 = st.columns(3)
    c1.metric("Universe", f"{universe['ticker'].nunique()} stocks")
    c2.metric("Price rows", f"{len(prices):,}")
    c3.metric(
        "Available dates",
        f"{prices['date'].min().date()} → {prices['date'].max().date()}",
    )

# Validation before calculation

if generate:
    selection_report = validator.validate_selection(
        universe=universe,
        prices=prices,
        selected_tickers=selected_tickers,
        start_date=start_date,
        end_date=end_date,
    )

    if selection_report.errors:
        st.subheader("Validation")

        for error in selection_report.errors:
            st.error(error)
        st.stop()

    prepared_prices = validator.prepare_prices_for_calculation(
        universe, prices
    )

    # Calculate weights
    selected_universe = universe[
        universe["ticker"].isin(selected_tickers)
    ].copy()

    try:
        if weighting_method == "Equal Weight":
            weights = weight_calculator.equal_weight(
                selected_universe
            )
        else:
            weights = weight_calculator.float_market_cap_weight(
                selected_universe
            )

        weight_calculator.validate_weights(weights)

        # Calculate the index
        index_data, detail_data = index_calculator.calculate(
            price_data=prepared_prices,
            weights=weights,
            start_date=start_date,
            end_date=end_date,
            base_level=base_level,
        )

    except ValueError as exc:
        st.subheader("Validation")
        st.error(str(exc))
        st.stop()

    summary = index_calculator.summarize(
        index_data, base_level=base_level
    )

    # Results

    st.subheader("Index Results")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Current Index Level",
        f"{summary['final_level']:.2f}",
    )
    col2.metric(
        "Cumulative Return",
        f"{summary['cumulative_return']:.2%}",
    )
    col3.metric(
        "Best Day",
        f"{summary['best_day']:.2%}",
    )
    col4.metric(
        "Worst Day",
        f"{summary['worst_day']:.2%}",
    )

    # Index chart
    st.subheader("Price Return Index")

    st.line_chart(
        index_data.set_index("date")["index_level"],
        height=400,
    )

    # Weights

    st.subheader("Weight Distribution")

    weight_display = (
        selected_universe[
            ["ticker", "company_name", "sector", "float_market_cap"]
        ]
        .set_index("ticker")
        .join(weights.rename("weight"))
        .sort_values("weight", ascending=False)
        )
    st.dataframe(
        weight_display.style.format(
            {
                "float_market_cap": "{:,.0f}",
                "weight": "{:.2%}",
            }
        ),
        use_container_width=True,
    )

    # Calculation integrity check

    reconciliation_ok = (index_calculator.validate_reconciliation(index_data,detail_data,))

    st.subheader("Calculation Validation")

    if abs(weights.sum() - 1.0) < 1e-10:
        st.success("Constituent weights sum to 100%.")
    else:
        st.error("Constituent weights do not sum to 100%.")

    if reconciliation_ok:
        st.success("Index return reconciles to the sum of constituent contributions.")
    else:
        st.error("Index return reconciliation failed.")

    st.info(
        "Price Return Index: dividends are not reinvested. "
        "Weights are fixed for the selected calculation period."
    )

    # Final Day Contribution

    st.subheader("Latest-Day Constituent Contributions")

    latest_date = detail_data["date"].max()

    contribution_table = (
        detail_data[
            detail_data["date"] == latest_date
        ][
            ["ticker", "weight", "daily_return", "contribution"]
        ]
        .sort_values("contribution", ascending=False)
        .reset_index(drop=True)
    )

    st.caption(
        f"Contribution analysis for {latest_date:%Y-%m-%d}"
    )

    st.dataframe(
        contribution_table.style.format(
            {
                "weight": "{:.2%}",
                "daily_return": "{:.2%}",
                "contribution": "{:.4%}",
            }
        ),
        use_container_width=True,
    )

    # Warnings specific to this run

    st.subheader("Run Validation")

    duplicate_count = int(
        prices[
            prices["ticker"].isin(selected_tickers)
        ].duplicated(["date", "ticker"]).sum()
    )

    if duplicate_count:
        st.warning(
            f"{duplicate_count} duplicate selected price row(s) were found "
            "in the source data. The calculation keeps the first "
            "observation for each date/ticker."
        )
    else:
        st.success("No duplicate selected price observations.")

    st.success(
        f"Generated using {len(selected_tickers)} constituent(s), "
        f"{weighting_method.lower()}, and {len(index_data)} index dates."
    )

# Default landing screen

else:
    st.info("Configure the index in the sidebar and click **Generate Index**."
    )

    st.subheader("How the Index Is Calculated")
    st.markdown(
        """
        **1. Stock's Daily Return**

        `return = close(t) / close(t-1) - 1`

        **2. Weighted Index Return**

        `index_return = sum(weight × constituent_return)`

        **3. Index Level**

        `level(t) = level(t-1) × (1 + index_return)`

        This calculation is **Price Return only** and does not reinvest dividends.
        """
    )