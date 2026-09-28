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

    st.subheader("Constituent Weights")

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
