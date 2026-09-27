from dataclasses import dataclass, field

import pandas as pd


@dataclass
class ValidationReport:
    """Store validation errors and warnings."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, message: str) -> None:
        self.errors.append(message)

    def add_warning(self, message: str) -> None:
        self.warnings.append(message)


class DataValidator:
    """Validate the structure and quality of financial data."""

    UNIVERSE_REQUIRED = {
        "ticker",
        "company_name",
        "sector",
        "float_market_cap",
    }

    PRICE_REQUIRED = {
        "date",
        "ticker",
        "close_price",
    }

    def validate(
        self,
        universe: pd.DataFrame,
        prices: pd.DataFrame,
    ) -> ValidationReport:

        report = ValidationReport()

        # -------------------------
        # Schema validation
        # -------------------------

        missing_universe = (
            self.UNIVERSE_REQUIRED
            - set(universe.columns)
        )

        missing_prices = (
            self.PRICE_REQUIRED
            - set(prices.columns)
        )

        if missing_universe:
            report.add_error(
                f"Universe missing columns: "
                f"{sorted(missing_universe)}"
            )

        if missing_prices:
            report.add_error(
                f"Prices missing columns: "
                f"{sorted(missing_prices)}"
            )

        # Don't continue with deeper checks if schema is invalid.
        if report.errors:
            return report

        # -------------------------
        # Universe checks
        # -------------------------

        if universe["ticker"].nunique() != 30:
            report.add_error(
                "Universe must contain exactly 30 unique tickers."
            )

        duplicate_tickers = (
            universe["ticker"].duplicated().sum()
        )

        if duplicate_tickers:
            report.add_error(
                f"Found {duplicate_tickers} duplicate "
                "ticker(s) in universe."
            )

        # -------------------------
        # Price-data checks
        # -------------------------

        duplicate_keys = prices.duplicated(
            ["date", "ticker"]
        ).sum()

        if duplicate_keys:
            report.add_warning(
                f"Found {duplicate_keys} duplicate "
                "(date, ticker) records."
            )

        missing_dates = prices["date"].isna().sum()

        if missing_dates:
            report.add_error(
                f"Found {missing_dates} invalid date value(s)."
            )

        missing_prices = prices["close_price"].isna().sum()

        if missing_prices:
            report.add_warning(
                f"Found {missing_prices} missing close-price value(s)."
            )

        non_positive_prices = (
            prices["close_price"]
            .le(0)
            .fillna(False)
            .sum()
        )

        if non_positive_prices:
            report.add_error(
                "Found non-positive close prices."
            )

        # -------------------------
        # Float market-cap checks
        # -------------------------

        invalid_fmc = (
            universe["float_market_cap"]
            .le(0)
            .fillna(True)
            .sum()
        )

        if invalid_fmc:
            report.add_error(
                "Found non-positive or missing "
                "float market-cap values."
            )

        # -------------------------
        # Ticker relationship
        # -------------------------

        unknown_tickers = sorted(
            set(prices["ticker"])
            - set(universe["ticker"])
        )

        if unknown_tickers:
            report.add_warning(
                "Price data contains ticker(s) not "
                f"in universe: {unknown_tickers}"
            )

        return report