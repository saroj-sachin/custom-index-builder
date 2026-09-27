from pathlib import Path

import pandas as pd


class DataLoader:
    """Load the project's universe and daily price data."""

    def __init__(self, data_dir: str | Path):
        self.data_dir = Path(data_dir)

    def load_universe(self) -> pd.DataFrame:
        """Load the 30-stock universe."""
        path = self.data_dir / "universe.csv"

        universe = pd.read_csv(path)

        return universe

    def load_prices(self) -> pd.DataFrame:
        """Load daily closing prices."""
        path = self.data_dir / "prices.csv"

        prices = pd.read_csv(path)

        prices["date"] = pd.to_datetime(
            prices["date"],
            errors="coerce"
        )

        prices["close_price"] = pd.to_numeric(
            prices["close_price"],
            errors="coerce"
        )

        return prices