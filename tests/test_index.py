import numpy as np
import pandas as pd
import pytest

from src.index_calculator import IndexCalculator
from src.weighting import WeightCalculator


def sample_universe():
    return pd.DataFrame(
        {
            "ticker": ["A", "B", "C"],
            "float_market_cap": [
                100.0,
                50.0,
                25.0,
            ],
        }
    )


def sample_prices():
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-01-01",
                    "2026-01-02",
                    "2026-01-03",
                    "2026-01-01",
                    "2026-01-02",
                    "2026-01-03",
                    "2026-01-01",
                    "2026-01-02",
                    "2026-01-03",
                ]
            ),
            "ticker": [
                "A", "A", "A",
                "B", "B", "B",
                "C", "C", "C",
            ],
            "close_price": [
                100, 110, 110,
                100, 100, 105,
                100, 98, 98,
            ],
        }
    )


def test_equal_weight():
    universe = sample_universe()

    weights = (
        WeightCalculator
        .equal_weight(universe)
    )

    assert np.allclose(
        weights.values,
        [1 / 3, 1 / 3, 1 / 3],
    )

    assert np.isclose(
        weights.sum(),
        1.0,
    )


def test_float_market_cap_weight():
    universe = sample_universe()

    weights = (
        WeightCalculator
        .float_market_cap_weight(
            universe
        )
    )

    assert np.allclose(
        weights.values,
        [
            100 / 175,
            50 / 175,
            25 / 175,
        ],
    )


def test_index_level():
    prices = sample_prices()

    weights = (
        WeightCalculator
        .equal_weight(
            sample_universe()
        )
    )

    calculator = IndexCalculator()

    index_data, _ = (
        calculator.calculate(
            prices,
            weights,
            "2026-01-01",
            "2026-01-03",
            base_level=100,
        )
    )

    assert np.isclose(
        index_data["index_level"].iloc[0],
        100,
    )


def test_reconciliation():
    prices = sample_prices()

    weights = (
        WeightCalculator
        .equal_weight(
            sample_universe()
        )
    )

    calculator = IndexCalculator()

    index_data, detail_data = (
        calculator.calculate(
            prices,
            weights,
            "2026-01-01",
            "2026-01-03",
        )
    )

    assert calculator.validate_reconciliation(
        index_data,
        detail_data,
    )


def test_empty_selection():
    with pytest.raises(ValueError):
        WeightCalculator.equal_weight(
            pd.DataFrame(
                columns=[
                    "ticker",
                    "float_market_cap",
                ]
            )
        )