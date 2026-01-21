# TechnicalAnalysis/MarketStructure/relations.py

import warnings

import numpy as np
import pandas as pd
import talib.abstract as ta

from TechnicalAnalysis.MarketStructure.utils import ensure_indicator


class PivotRelations:
    def apply(self, df) -> dict[str, pd.Series]:
        return self._detect_eqh_eql_from_pivots(df)


    def _detect_eqh_eql_from_pivots(
        self,
        df: pd.DataFrame,
        eq_atr_mult: float = 0.2,
        prefix: str = "",
    ) -> dict[str, pd.Series]:

        ensure_indicator(df, indicator="atr", period=14)

        # =========================
        # Threshold
        # =========================
        eq_threshold = df["atr"] * eq_atr_mult

        # =========================
        # EQH: HH–HH
        # =========================
        eqh_hh = (
            df["HH_idx"].notna()
            & df["HH_idx_shift"].notna()
            & (df["HH_idx"] != df["HH_idx_shift"])
            & ((df["HH"] - df["HH_shift"]).abs() <= eq_threshold)
        )

        # =========================
        # EQH: HH–LH
        # =========================
        eqh_hh_lh = (
            df["LH_idx"].notna()
            & df["HH_idx"].notna()
            & (df["LH_idx"] > df["HH_idx"])
            & (df["LH_idx"] != df["LH_idx_shift"])
            & ((df["LH"] - df["HH"]).abs() <= eq_threshold)
        )

        EQH = eqh_hh | eqh_hh_lh

        EQH_level = pd.Series(np.nan, index=df.index)
        EQH_level[eqh_hh] = df["HH"][eqh_hh]
        EQH_level[eqh_hh_lh] = df["HH"][eqh_hh_lh]
        EQH_level = EQH_level.ffill()

        # =========================
        # EQL: LL–LL
        # =========================
        eql_ll = (
            df["LL_idx"].notna()
            & df["LL_idx_shift"].notna()
            & (df["LL_idx"] != df["LL_idx_shift"])
            & ((df["LL"] - df["LL_shift"]).abs() <= eq_threshold)
        )

        # =========================
        # EQL: LL–HL
        # =========================
        eql_ll_hl = (
            df["HL_idx"].notna()
            & df["LL_idx"].notna()
            & (df["HL_idx"] > df["LL_idx"])
            & (df["HL_idx"] != df["HL_idx_shift"])
            & ((df["HL"] - df["LL"]).abs() <= eq_threshold)
        )

        EQL = eql_ll | eql_ll_hl

        EQL_level = pd.Series(np.nan, index=df.index)
        EQL_level[eql_ll] = df["LL"][eql_ll]
        EQL_level[eql_ll_hl] = df["LL"][eql_ll_hl]
        EQL_level = EQL_level.ffill()

        # =========================
        # OUTPUT (BATCH)
        # =========================
        return {
            f"{prefix}EQH": EQH,
            f"{prefix}EQH_level": EQH_level,
            f"{prefix}EQL": EQL,
            f"{prefix}EQL_level": EQL_level,
        }