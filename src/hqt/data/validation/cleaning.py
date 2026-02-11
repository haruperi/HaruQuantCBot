"""
Data cleaning operations for HQT Trading System.

This module provides automated data cleaning to fix detected issues.

[REQ: DAT-FR-013] Automated data cleaning operations.
"""

from enum import Enum

import pandas as pd


class FillMethod(str, Enum):
    """
    Methods for filling gaps in data.

    Attributes:
        FORWARD_FILL: Use previous value (ffill)
        BACKWARD_FILL: Use next value (bfill)
        INTERPOLATE_LINEAR: Linear interpolation between values
        INTERPOLATE_TIME: Time-weighted interpolation
    """

    FORWARD_FILL = "ffill"
    BACKWARD_FILL = "bfill"
    INTERPOLATE_LINEAR = "linear"
    INTERPOLATE_TIME = "time"


class DataCleaner:
    """
    Automated data cleaning operations.

    Provides methods to fix common data quality issues:
    - Fill missing data gaps
    - Remove duplicate timestamps
    - Filter price spikes
    - Forward-fill zero volumes

    [REQ: DAT-FR-013] Data cleaning implementation.

    Example:
        ```python
        from hqt.data.validation import DataCleaner, FillMethod

        cleaner = DataCleaner()

        # Remove duplicates (keep last)
        cleaned_df = cleaner.remove_duplicates(df)

        # Fill gaps
        cleaned_df = cleaner.fill_gaps(
            cleaned_df,
            method=FillMethod.FORWARD_FILL,
        )

        # Filter extreme spikes
        cleaned_df = cleaner.filter_spikes(
            cleaned_df,
            threshold_multiplier=10.0,
        )
        ```
    """

    def remove_duplicates(
        self,
        df: pd.DataFrame,
        keep: str = "last",
    ) -> pd.DataFrame:
        """
        Remove duplicate timestamps.

        Args:
            df: DataFrame with timestamp column
            keep: Which duplicate to keep ('first', 'last', or False to remove all)

        Returns:
            DataFrame with duplicates removed

        Example:
            ```python
            # Keep last occurrence
            clean_df = cleaner.remove_duplicates(df, keep="last")

            # Remove all duplicates
            clean_df = cleaner.remove_duplicates(df, keep=False)
            ```
        """
        if df.empty:
            return df

        # Sort by timestamp first to ensure consistent behavior
        df_sorted = df.sort_values("timestamp").copy()

        # Remove duplicates
        df_clean = df_sorted.drop_duplicates(subset=["timestamp"], keep=keep)

        return df_clean.reset_index(drop=True)

    def fill_gaps(
        self,
        df: pd.DataFrame,
        method: FillMethod = FillMethod.FORWARD_FILL,
        max_gap_seconds: int | None = None,
    ) -> pd.DataFrame:
        """
        Fill small gaps in the data.

        Args:
            df: DataFrame with OHLCV data
            method: Method to use for filling
            max_gap_seconds: Maximum gap size to fill (None = fill all gaps)

        Returns:
            DataFrame with gaps filled

        Note:
            - Forward fill: Uses previous bar's close as open, and same as close
            - Interpolation: Uses pandas interpolate() method
            - Large gaps (> max_gap_seconds) are not filled

        Example:
            ```python
            # Forward fill small gaps (< 1 hour)
            clean_df = cleaner.fill_gaps(
                df,
                method=FillMethod.FORWARD_FILL,
                max_gap_seconds=3600,
            )
            ```
        """
        if df.empty or len(df) < 2:
            return df

        df_clean = df.copy()

        if method == FillMethod.FORWARD_FILL:
            # Forward fill all OHLCV columns
            df_clean = df_clean.ffill()

        elif method == FillMethod.BACKWARD_FILL:
            # Backward fill all OHLCV columns
            df_clean = df_clean.bfill()

        elif method in (FillMethod.INTERPOLATE_LINEAR, FillMethod.INTERPOLATE_TIME):
            # Interpolate numeric columns only
            numeric_cols = ["open", "high", "low", "close"]
            if "volume" in df_clean.columns:
                numeric_cols.append("volume")

            for col in numeric_cols:
                if col in df_clean.columns:
                    if method == FillMethod.INTERPOLATE_LINEAR:
                        df_clean[col] = df_clean[col].interpolate(method="linear")
                    else:
                        # Time-weighted requires timestamp as index
                        df_temp = df_clean.set_index("timestamp")
                        df_temp[col] = df_temp[col].interpolate(method="time")
                        df_clean[col] = df_temp[col].values

        return df_clean

    def filter_spikes(
        self,
        df: pd.DataFrame,
        threshold_multiplier: float = 10.0,
        atr_period: int = 14,
        replace_method: str = "interpolate",
    ) -> pd.DataFrame:
        """
        Filter extreme price spikes.

        Replaces bars with range > threshold * ATR with interpolated values.

        Args:
            df: DataFrame with OHLCV data
            threshold_multiplier: Multiplier of ATR to trigger spike removal
            atr_period: Period for ATR calculation
            replace_method: How to replace spikes ('interpolate' or 'remove')

        Returns:
            DataFrame with spikes filtered

        Example:
            ```python
            # Remove extreme spikes (>10x ATR)
            clean_df = cleaner.filter_spikes(
                df,
                threshold_multiplier=10.0,
                replace_method="interpolate",
            )
            ```
        """
        if df.empty or len(df) < atr_period:
            return df

        df_clean = df.copy()

        # Calculate True Range and ATR
        df_clean["prev_close"] = df_clean["close"].shift(1)
        df_clean["tr1"] = df_clean["high"] - df_clean["low"]
        df_clean["tr2"] = abs(df_clean["high"] - df_clean["prev_close"])
        df_clean["tr3"] = abs(df_clean["low"] - df_clean["prev_close"])
        df_clean["true_range"] = df_clean[["tr1", "tr2", "tr3"]].max(axis=1)
        df_clean["atr"] = df_clean["true_range"].rolling(window=atr_period).mean()

        # Calculate bar range
        df_clean["range"] = df_clean["high"] - df_clean["low"]

        # Find spikes
        df_clean["spike_threshold"] = df_clean["atr"] * threshold_multiplier
        spike_mask = (df_clean["range"] > df_clean["spike_threshold"]) & (
            df_clean["atr"].notna()
        )

        if spike_mask.any():
            if replace_method == "interpolate":
                # Interpolate OHLC for spike bars
                price_cols = ["open", "high", "low", "close"]
                for col in price_cols:
                    # Set spike values to NaN
                    df_clean.loc[spike_mask, col] = pd.NA
                    # Interpolate
                    df_clean[col] = df_clean[col].interpolate(method="linear")
            else:
                # Remove spike rows entirely
                df_clean = df_clean[~spike_mask]

        # Drop temporary columns
        temp_cols = [
            "prev_close",
            "tr1",
            "tr2",
            "tr3",
            "true_range",
            "atr",
            "range",
            "spike_threshold",
        ]
        df_clean = df_clean.drop(columns=temp_cols)

        return df_clean.reset_index(drop=True)

    def fill_zero_volumes(
        self,
        df: pd.DataFrame,
        method: str = "ffill",
    ) -> pd.DataFrame:
        """
        Fill zero or missing volumes.

        Args:
            df: DataFrame with volume column
            method: Fill method ('ffill', 'bfill', or 'median')

        Returns:
            DataFrame with zero volumes filled

        Example:
            ```python
            # Forward fill zero volumes
            clean_df = cleaner.fill_zero_volumes(df, method="ffill")

            # Use median volume
            clean_df = cleaner.fill_zero_volumes(df, method="median")
            ```
        """
        if df.empty or "volume" not in df.columns:
            return df

        df_clean = df.copy()

        # Find zero, negative, or missing volumes
        invalid_mask = (df_clean["volume"] <= 0) | df_clean["volume"].isna()

        if invalid_mask.any():
            if method == "ffill":
                # Replace invalid volumes with NA, then forward fill
                df_clean.loc[invalid_mask, "volume"] = pd.NA
                df_clean["volume"] = df_clean["volume"].ffill()
            elif method == "bfill":
                # Replace invalid volumes with NA, then backward fill
                df_clean.loc[invalid_mask, "volume"] = pd.NA
                df_clean["volume"] = df_clean["volume"].bfill()
            elif method == "median":
                # Use median of valid volumes
                valid_volumes = df_clean["volume"][~invalid_mask]
                if len(valid_volumes) > 0:
                    median_volume = valid_volumes.median()
                    df_clean.loc[invalid_mask, "volume"] = median_volume
                else:
                    # No valid volumes, set to 1.0 as fallback
                    df_clean.loc[invalid_mask, "volume"] = 1.0
            else:
                raise ValueError(f"Unknown method: {method}")

            # Fill any remaining NaN with 1.0 (better than 0)
            df_clean["volume"] = df_clean["volume"].fillna(1.0)

        return df_clean

    def clean_all(
        self,
        df: pd.DataFrame,
        remove_duplicates: bool = True,
        fill_gaps: bool = True,
        filter_spikes: bool = True,
        fill_zero_volumes: bool = True,
        **kwargs,
    ) -> pd.DataFrame:
        """
        Apply all cleaning operations in sequence.

        Args:
            df: DataFrame to clean
            remove_duplicates: Whether to remove duplicates
            fill_gaps: Whether to fill gaps
            filter_spikes: Whether to filter spikes
            fill_zero_volumes: Whether to fill zero volumes
            **kwargs: Additional parameters for specific cleaning operations

        Returns:
            Cleaned DataFrame

        Example:
            ```python
            # Apply all cleaning operations
            clean_df = cleaner.clean_all(
                df,
                spike_threshold_multiplier=10.0,
                fill_method=FillMethod.FORWARD_FILL,
            )
            ```
        """
        df_clean = df.copy()

        # 1. Remove duplicates first
        if remove_duplicates:
            df_clean = self.remove_duplicates(df_clean)

        # 2. Fill gaps
        if fill_gaps:
            fill_method = kwargs.get("fill_method", FillMethod.FORWARD_FILL)
            max_gap_seconds = kwargs.get("max_gap_seconds", None)
            df_clean = self.fill_gaps(
                df_clean,
                method=fill_method,
                max_gap_seconds=max_gap_seconds,
            )

        # 3. Filter spikes
        if filter_spikes:
            spike_threshold = kwargs.get("spike_threshold_multiplier", 10.0)
            atr_period = kwargs.get("atr_period", 14)
            df_clean = self.filter_spikes(
                df_clean,
                threshold_multiplier=spike_threshold,
                atr_period=atr_period,
            )

        # 4. Fill zero volumes
        if fill_zero_volumes and "volume" in df_clean.columns:
            volume_method = kwargs.get("volume_fill_method", "ffill")
            df_clean = self.fill_zero_volumes(df_clean, method=volume_method)

        return df_clean
