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

