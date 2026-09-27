import numpy as np
import pandas as pd


class IndexCalculator:
    """Calculate a weighted Price Return Index."""

    @staticmethod
    def add_daily_returns(
        price_data: pd.DataFrame,
    ) -> pd.DataFrame:

        df = price_data.copy()

        df = df.sort_values(
            ["ticker", "date"]
        )

        df["daily_return"] = (
            df.groupby("ticker")["close_price"]
            .pct_change()
        )

        return df

    def calculate(
        self,
        price_data: pd.DataFrame,
        weights: pd.Series,
        start_date,
        end_date,
        base_level: float = 100.0,
    ) -> tuple[pd.DataFrame, pd.DataFrame]:

        if weights.empty:
            raise ValueError(
                "Weights cannot be empty."
            )

        if base_level <= 0:
            raise ValueError(
                "Base level must be positive."
            )

        # Keep only selected securities.
        df = price_data[
            price_data["ticker"].isin(weights.index)
        ].copy()

        # Calculate returns before filtering the selected date range.
        df = self.add_daily_returns(df)

        # Apply requested date range.
        df = df[
            df["date"].between(
                pd.Timestamp(start_date),
                pd.Timestamp(end_date),
            )
        ].copy()

        if df.empty:
            raise ValueError(
                "No data available for the selected "
                "securities and dates."
            )

        # The first displayed date is treated as the base date.
        first_date = df["date"].min()

        df.loc[
            df["date"] == first_date,
            "daily_return",
        ] = 0.0

        # Every selected security must have a return
        # on every index date.
        return_counts = (
            df.dropna(subset=["daily_return"])
            .groupby("date")["ticker"]
            .nunique()
        )

        expected_count = len(weights)

        incomplete_dates = return_counts[
            return_counts != expected_count
        ]

        if not incomplete_dates.empty:
            bad_dates = [
                date.strftime("%Y-%m-%d")
                for date in incomplete_dates.index
            ]

            raise ValueError(
                "Incomplete constituent coverage on: "
                f"{bad_dates}"
            )

        # Attach the selected weights.
        df["weight"] = df["ticker"].map(weights)

        if df["weight"].isna().any():
            raise ValueError(
                "Unable to match weights to all securities."
            )

        # Individual constituent contribution.
        df["contribution"] = (
            df["weight"]
            * df["daily_return"]
        )

        # Weighted index return.
        daily = (
            df.groupby("date", as_index=False)
            .agg(
                index_return=(
                    "contribution",
                    "sum",
                )
            )
            .sort_values("date")
            .reset_index(drop=True)
        )

        # Build the index level.
        daily["index_level"] = (
            (1 + daily["index_return"])
            .cumprod()
            * base_level
        )

        # Cumulative return relative to base.
        daily["cumulative_return"] = (
            daily["index_level"]
            / base_level
            - 1
        )

        return daily, df

    @staticmethod
    def summarize(
        index_data: pd.DataFrame,
        base_level: float = 100.0,
    ) -> dict:

        if index_data.empty:
            raise ValueError(
                "Index data cannot be empty."
            )

        final_level = float(
            index_data["index_level"].iloc[-1]
        )

        return {
            "initial_level": base_level,
            "final_level": final_level,
            "cumulative_return": (
                final_level / base_level - 1
            ),
            "best_day": float(
                index_data["index_return"].max()
            ),
            "worst_day": float(
                index_data["index_return"].min()
            ),
        }

    @staticmethod
    def validate_reconciliation(
        index_data: pd.DataFrame,
        detail_data: pd.DataFrame,
        tolerance: float = 1e-12,
    ) -> bool:

        calculated = (
            detail_data
            .groupby("date")["contribution"]
            .sum()
            .sort_index()
        )

        reported = (
            index_data
            .set_index("date")["index_return"]
            .sort_index()
        )

        return np.allclose(
            calculated.values,
            reported.values,
            atol=tolerance,
            rtol=0,
        )