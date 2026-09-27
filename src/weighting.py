import pandas as pd


class WeightCalculator:
    """Calculate constituent weights."""

    @staticmethod
    def equal_weight(
        selected_universe: pd.DataFrame,
    ) -> pd.Series:

        if selected_universe.empty:
            raise ValueError(
                "At least one security must be selected."
            )

        n = len(selected_universe)

        weights = pd.Series(
            1 / n,
            index=selected_universe["ticker"],
            name="weight",
        )

        return weights

    @staticmethod
    def float_market_cap_weight(
        selected_universe: pd.DataFrame,
    ) -> pd.Series:

        if selected_universe.empty:
            raise ValueError(
                "At least one security must be selected."
            )

        total_market_cap = (
            selected_universe["float_market_cap"]
            .sum()
        )

        if total_market_cap <= 0:
            raise ValueError(
                "Total float market capitalization "
                "must be positive."
            )

        weights = (
            selected_universe
            .set_index("ticker")["float_market_cap"]
            / total_market_cap
        )

        weights.name = "weight"

        return weights

    @staticmethod
    def validate_weights(
        weights: pd.Series,
        tolerance: float = 1e-10,
    ) -> None:

        if weights.empty:
            raise ValueError(
                "Weights cannot be empty."
            )

        if weights.isna().any():
            raise ValueError(
                "Weights cannot contain missing values."
            )

        if (weights < 0).any():
            raise ValueError(
                "Weights cannot be negative."
            )

        if abs(weights.sum() - 1) > tolerance:
            raise ValueError(
                "Weights must sum to 1."
            )