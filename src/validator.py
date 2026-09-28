from dataclasses import dataclass, field
import pandas as pd


@dataclass
class ValidationReport:
    """Container for validation findings."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


class DataValidator:
    """Validate the structure and basic quality of input data."""

    UNIVERSE_REQUIRED = {
        "ticker",
        "company_name",
        "sector",
        "float_market_cap",
    }

    PRICE_REQUIRED = {"date", "ticker", "close_price"}

    def validate(
        self,
        universe: pd.DataFrame,
        prices: pd.DataFrame,
    ) -> ValidationReport:
        report = ValidationReport()

        missing_universe = self.UNIVERSE_REQUIRED - set(universe.columns)
        missing_prices = self.PRICE_REQUIRED - set(prices.columns)

        if missing_universe:
            report.add_error(
                f"Universe is missing required columns: "
                f"{sorted(missing_universe)}"
            )

        if missing_prices:
            report.add_error(
                f"Prices are missing required columns: "
                f"{sorted(missing_prices)}"
            )

        # Stop deeper checks if the schema is incomplete.
        if report.errors:
            return report

        if universe["ticker"].nunique() != 30:
            report.add_error(
                "The stock universe must contain exactly 30 unique tickers."
            )

        duplicate_universe = int(universe["ticker"].duplicated().sum())
        if duplicate_universe:
            report.add_error(
                f"Universe contains {duplicate_universe} duplicate ticker row(s)."
            )

        duplicate_price_keys = int(
            prices.duplicated(["date", "ticker"]).sum()
        )
        if duplicate_price_keys:
            report.add_warning(
                f"Prices contain {duplicate_price_keys} duplicate "
                "(date, ticker) row(s). The application keeps the first "
                "observation and reports the issue."
            )

        missing_dates = int(prices["date"].isna().sum())
        if missing_dates:
            report.add_error(
                f"Prices contain {missing_dates} row(s) with invalid dates."
            )

        missing_close = int(prices["close_price"].isna().sum())
        if missing_close:
            report.add_warning(
                f"Prices contain {missing_close} missing close-price value(s). "
                "A calculation is blocked only when a selected constituent "
                "has missing data in the requested date range."
            )

        non_positive = int((prices["close_price"] <= 0).fillna(False).sum())
        if non_positive:
            report.add_error(
                f"Prices contain {non_positive} non-positive close-price value(s)."
            )

        invalid_float = int(
            (~universe["float_factor"].between(0, 1)).fillna(True).sum()
        )
        if invalid_float:
            report.add_error(
                f"Universe contains {invalid_float} invalid float-factor value(s)."
            )

        invalid_fmc = int(
            (universe["float_market_cap"] <= 0).fillna(True).sum()
        )
        if invalid_fmc:
            report.add_error(
                f"Universe contains {invalid_fmc} non-positive float "
                "market-cap value(s)."
            )

        unknown_tickers = sorted(
            set(prices["ticker"].dropna()) - set(universe["ticker"].dropna())
        )
        if unknown_tickers:
            report.add_warning(
                "Prices contain ticker(s) not present in the universe: "
                f"{unknown_tickers}. They are excluded from index calculations."
            )

        return report

    def validate_selection(
        self,
        universe: pd.DataFrame,
        prices: pd.DataFrame,
        selected_tickers: list[str],
        start_date,
        end_date,
    ) -> ValidationReport:
        report = ValidationReport()

        if not selected_tickers:
            report.add_error("Select at least one constituent.")

        if start_date is None or end_date is None:
            report.add_error("Both start date and end date are required.")
            return report

        if start_date >= end_date:
            report.add_error("Start date must be earlier than end date.")

        known_tickers = set(universe["ticker"])
        unknown_selection = sorted(
            set(selected_tickers) - known_tickers
        )
        if unknown_selection:
            report.add_error(
                f"Selected ticker(s) are not in the universe: {unknown_selection}"
            )

        selected_prices = prices[
            prices["ticker"].isin(selected_tickers)
            & prices["date"].between(
                pd.Timestamp(start_date),
                pd.Timestamp(end_date),
            )
        ].copy()

        if not selected_prices.empty:
            missing_selected = (
                selected_prices.groupby("ticker")["close_price"]
                .apply(lambda s: s.isna().any())
            )
            missing_selected = missing_selected[
                missing_selected
            ].index.tolist()

            if missing_selected:
                report.add_error(
                    "Missing close-price data found for selected "
                    f"constituent(s): {missing_selected}. "
                    "For this prototype, calculation is stopped rather "
                    "than silently imputing prices."
                )

            negative_selected = (
                selected_prices["close_price"].le(0).fillna(False).sum()
            )
            if negative_selected:
                report.add_error(
                    "Selected data contain non-positive close prices."
                )

        # Each selected security needs one usable observation on every date.
        unique_dates = prices[
            prices["date"].between(
                pd.Timestamp(start_date),
                pd.Timestamp(end_date),
            )
        ]["date"].drop_duplicates()

        if len(unique_dates) < 2:
            report.add_error(
                "The selected range must contain at least two available dates."
            )

        return report

    @staticmethod
    def prepare_prices_for_calculation(
        universe: pd.DataFrame,
        prices: pd.DataFrame,
    ) -> pd.DataFrame:
        """Return a deterministic calculation set.

        Duplicate (date, ticker) rows are reduced to the first observation.
        Tickers outside the official universe are excluded.
        """
        valid_tickers = set(universe["ticker"])
        prepared = prices[
            prices["ticker"].isin(valid_tickers)
        ].copy()

        prepared = (
            prepared.sort_values(["ticker", "date"])
            .drop_duplicates(["date", "ticker"], keep="first")
            .reset_index(drop=True)
        )
        return prepared
