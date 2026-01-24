#TechnicalAnalysis/PriceAction_Fibbonaci/core.py
import numpy as np
import pandas as pd

from TechnicalAnalysis.MarketStructure.engine import MarketStructureEngine
from TechnicalAnalysis.MarketStructure.pivots import PivotDetector, PivotDetectorBatched
from TechnicalAnalysis.MarketStructure.price_action_liquidity import PriceActionLiquidityResponse, \
    PriceActionLiquidityResponseBatched
from TechnicalAnalysis.MarketStructure.relations import PivotRelations, PivotRelationsBatched
from TechnicalAnalysis.MarketStructure.fibo import FiboCalculator, FiboBatched
from TechnicalAnalysis.MarketStructure.price_action import PriceActionStateEngine, PriceActionStateEngineBatched
from TechnicalAnalysis.MarketStructure.follow_through import PriceActionFollowThrough, PriceActionFollowThroughBatched
from TechnicalAnalysis.MarketStructure.structural_volatility import PriceActionStructuralVolatility, \
    PriceActionStructuralVolatilityBatched
from TechnicalAnalysis.MarketStructure.trend_regime import PriceActionTrendRegime, PriceActionTrendRegimeBatched


class IntradayMarketStructure:
    """
    Deterministic intraday market structure pipeline.

    Responsibilities:
    - compute structural features (pivots, PA, liquidity, volatility, regime)
    - NO signals
    - NO execution logic
    - NO experimental features
    """

    def __init__(
        self,
        pivot_range: int = 15,
        min_percentage_change: float = 0.01,
        use_engine: bool = False,
    ):
        self.pivot_range = pivot_range
        self.min_percentage_change = min_percentage_change
        self.use_engine = use_engine

        # =========================
        # FIBO DEFINITIONS
        # =========================
        self.fibo_swing = FiboCalculator(
            pivot_range=pivot_range,
            mode="swing",
            prefix="fibo_swing",
        )

        self.fibo_range = FiboCalculator(
            pivot_range=pivot_range,
            mode="range",
            prefix="fibo_range",
        )

        # =========================
        # PRICE ACTION
        # =========================
        self.price_action_engine = PriceActionStateEngine()

        # =========================
        # ENGINE (PARTIAL, FUTURE)
        # =========================
        self.engine = MarketStructureEngine(
            pivot_detector=PivotDetector(self.pivot_range),
            relations=PivotRelations(),
            fibo=None,
            price_action=None,
        )

    # =============================================================
    # PUBLIC ENTRYPOINT
    # =============================================================
    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.use_engine:
            return self.apply_engine(df)
        return self.apply_legacy(df)

    # =============================================================
    # LEGACY PIPELINE (CLEAN, BATCH)
    # =============================================================
    def apply_legacy(self, df: pd.DataFrame) -> pd.DataFrame:
        # ======================================================
        # helpers
        # ======================================================
        def equal_series(a: pd.Series, b: pd.Series) -> bool:
            return (
                a.fillna(-1).astype(int)
                .equals(b.fillna(-1).astype(int))
            )

        def eq(a: pd.Series, b: pd.Series) -> bool:
            return a.fillna(-1).equals(b.fillna(-1))

        # ======================================================
        # 1️⃣ PIVOTS
        # ======================================================
        pivots_legacy = PivotDetector(self.pivot_range).apply(df)
        df_legacy = df.assign(**pivots_legacy)

        pivots_batched = PivotDetectorBatched(self.pivot_range).apply(df)

        for k in pivots_legacy:
            assert equal_series(pivots_legacy[k], pivots_batched[k]), f"PIVOT {k}"

        print("✅ PIVOTS: 1:1 OK")

        # ======================================================
        # 2️⃣ PIVOT RELATIONS (EQH / EQL)
        # ======================================================
        relations_legacy = PivotRelations().apply(df_legacy)
        relations_batched = PivotRelationsBatched().apply(
            pivots=pivots_batched,
            atr=df["atr"],
        )

        for k in relations_legacy:
            assert equal_series(relations_legacy[k], relations_batched[k]), f"REL {k}"

        print("✅ PIVOT RELATIONS: 1:1 OK")

        # ======================================================
        # 3️⃣ FIBO (SWING)
        # ======================================================
        fibo_legacy = FiboCalculator(
            pivot_range=self.pivot_range,
            mode="swing",
            prefix="fibo_swing",
        ).apply(df_legacy)

        fibo_batched = FiboBatched(
            pivot_range=self.pivot_range,
            mode="swing",
            prefix="fibo_swing",
        ).apply(pivots=pivots_batched)

        for k in fibo_legacy:
            assert eq(fibo_legacy[k], fibo_batched[k]), f"FIBO {k}"

        print("✅ FIBO: 1:1 OK")

        # ======================================================
        # 4️⃣ PRICE ACTION STATE (BOS / MSS)
        # ======================================================
        pa_legacy = PriceActionStateEngine().apply(df_legacy)
        df_legacy = df_legacy.assign(**pa_legacy)

        pa_batched = PriceActionStateEngineBatched().apply(
            pivots=pivots_legacy,
            close=df["close"],
        )

        for k in pa_legacy:
            assert eq(pa_legacy[k], pa_batched[k]), f"PA STATE {k}"

        print("✅ PRICE ACTION STATE: 1:1 OK")

        # ======================================================
        # 5️⃣ FOLLOW THROUGH (BOS + MSS)
        # ======================================================
        ft_legacy_bos = PriceActionFollowThrough(event_source="bos").apply(df_legacy)
        df_legacy = df_legacy.assign(**ft_legacy_bos)
        ft_legacy_mss = PriceActionFollowThrough(event_source="mss").apply(df_legacy)
        df_legacy = df_legacy.assign(**ft_legacy_mss)



        ft_bos = PriceActionFollowThroughBatched(
            event_source="bos",
            atr_mult=1.0,
            lookahead=5,
        ).apply(
            events={
                "bos_bull_event": pa_batched["bos_bull_event"],
                "bos_bear_event": pa_batched["bos_bear_event"],
            },
            levels={
                "bos_bull_level": pa_batched["bos_bull_level"],
                "bos_bear_level": pa_batched["bos_bear_level"],
            },
            high=df["high"],
            low=df["low"],
            atr=df["atr"],
        )

        ft_mss = PriceActionFollowThroughBatched(
            event_source="mss",
            atr_mult=1.0,
            lookahead=5,
        ).apply(
            events={
                "mss_bull_event": pa_batched["mss_bull_event"],
                "mss_bear_event": pa_batched["mss_bear_event"],
            },
            levels={
                "mss_bull_level": pa_batched["mss_bull_level"],
                "mss_bear_level": pa_batched["mss_bear_level"],
            },
            high=df["high"],
            low=df["low"],
            atr=df["atr"],
        )

        for k in ft_legacy_bos:
            assert eq(ft_legacy_bos[k], ft_bos[k]), f"FT {k}"

        print("✅ FOLLOW THROUGH: 1:1 OK")

        # ======================================================
        # 6️⃣ LIQUIDITY RESPONSE (BOS BULL)
        # ======================================================
        liq_legacy = PriceActionLiquidityResponse(
            event_source="bos",
            direction="bull",
        ).apply(df_legacy)

        liq_batched = PriceActionLiquidityResponseBatched(
            event_source="bos",
            direction="bull",
        ).apply(
            events={"bos_bull_event": pa_batched["bos_bull_event"]},
            levels={"bos_bull_level": pa_batched["bos_bull_level"]},
            follow_through={
                "bos_bull_ft_valid": ft_bos["bos_bull_ft_valid"],
                "bos_bull_ft_weak": ft_bos["bos_bull_ft_weak"],},
            df=df,
        )



        diff_liq = liq_legacy["sr_flip_bos_bull"].compare(
            liq_batched["sr_flip_bos_bull"]
        )

        print("FIRST LIQ DIFF:")
        print(diff_liq.head(10))
        print("LIQ DIFF INDEX:")
        print(diff_liq.index[:10])

        for k in liq_legacy:
            assert eq(liq_legacy[k], liq_batched[k]), f"LIQ {k}"

        print("✅ LIQUIDITY RESPONSE: 1:1 OK")

        # ======================================================
        # 7️⃣ STRUCTURAL VOLATILITY (BOS BULL)
        # ======================================================
        sv_legacy_bos_bull = PriceActionStructuralVolatility(
            event_source="bos",
            direction="bull",
        ).apply(df_legacy)

        df_legacy = df_legacy.assign(**sv_legacy_bos_bull)

        sv_legacy_bos_bear = PriceActionStructuralVolatility(
            event_source="bos",
            direction="bear",
        ).apply(df_legacy)

        df_legacy = df_legacy.assign(**sv_legacy_bos_bear)

        ###

        sv_legacy_mss_bull = PriceActionStructuralVolatility(
            event_source="mss",
            direction="bull",
        ).apply(df_legacy)

        df_legacy = df_legacy.assign(**sv_legacy_mss_bull)

        sv_legacy_mss_bear = PriceActionStructuralVolatility(
            event_source="mss",
            direction="bear",
        ).apply(df_legacy)

        df_legacy = df_legacy.assign(**sv_legacy_mss_bear)




        sv_batched_bos_bull = PriceActionStructuralVolatilityBatched(
            event_source="bos",
            direction="bull",
        ).apply(
            events={"bos_bull_event": pa_batched["bos_bull_event"]},
            df=df,
        )
        sv_batched_bos_bear = PriceActionStructuralVolatilityBatched(
            event_source="bos",
            direction="bear",
        ).apply(
            events={"bos_bear_event": pa_batched["bos_bear_event"]},
            df=df,
        )
        ###
        sv_batched_mss_bull = PriceActionStructuralVolatilityBatched(
            event_source="mss",
            direction="bull",
        ).apply(
            events={"mss_bull_event": pa_batched["mss_bull_event"]},
            df=df,
        )
        sv_batched_mss_bear = PriceActionStructuralVolatilityBatched(
            event_source="mss",
            direction="bear",
        ).apply(
            events={"mss_bear_event": pa_batched["mss_bear_event"]},
            df=df,
        )

        for k in sv_legacy_bos_bull:
            assert eq(sv_legacy_bos_bull[k], sv_batched_bos_bull[k]), f"SV {k}"

        print("✅ STRUCTURAL VOLATILITY: 1:1 OK")



        # ======================================================
        # 8️⃣ TREND REGIME (FINAL)
        # ======================================================
        trend_legacy = PriceActionTrendRegime().apply(df_legacy)

        print("LEGACY trend_regime", trend_legacy["trend_regime"].value_counts())
        print("LEGACY trend_bias", trend_legacy["trend_bias"].value_counts())
        print("LEGACY trend_strength", trend_legacy["trend_strength"].value_counts())

        trend_batched = PriceActionTrendRegimeBatched().apply(
            pivots={"pivot": pivots_batched["pivot"]},
            events={
                "bos_bull_event": pa_batched["bos_bull_event"],
                "bos_bear_event": pa_batched["bos_bear_event"],
                "mss_bull_event": pa_batched["mss_bull_event"],
                "mss_bear_event": pa_batched["mss_bear_event"],
                "bos_bull_ft_valid": ft_bos["bos_bull_ft_valid"],
                "bos_bear_ft_valid": ft_bos["bos_bear_ft_valid"],
                "mss_bull_ft_valid": ft_mss["mss_bull_ft_valid"],
                "mss_bear_ft_valid": ft_mss["mss_bear_ft_valid"],
            },
            struct_vol={
                "bos_bull_struct_vol": sv_batched_bos_bull["bos_bull_struct_vol"],
                "bos_bear_struct_vol": sv_batched_bos_bear["bos_bear_struct_vol"],
                "mss_bull_struct_vol": sv_batched_mss_bull["mss_bull_struct_vol"],
                "mss_bear_struct_vol": sv_batched_mss_bear["mss_bear_struct_vol"],
            },
            df=df
        )

        diff = trend_legacy["trend_regime"].compare(
            trend_batched["trend_regime"]
        )

        print("FIRST DIFF:")
        print(diff.head(10))

        print("DIFF INDEX:")
        print(diff.index[:10])

        for k in trend_legacy:
            assert trend_legacy[k].fillna("NA").equals(
                trend_batched[k].fillna("NA")
            ), f"TREND {k}"

        print("✅ TREND REGIME: 1:1 OK")

        return df

    # =============================================================
    # ENGINE PIPELINE (PLACEHOLDER)
    # =============================================================
    def apply_engine(self, df: pd.DataFrame) -> pd.DataFrame:
        out = self.engine.apply(df)
        return df.assign(**out)

    # =============================================================
    # DETECTORS (PURE FUNCTIONS)
    # =============================================================
    def detect_peaks(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        return PivotDetector(self.pivot_range).apply(df)

    def detect_eqh_eql_from_pivots(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        return PivotRelations().apply(df)

    def detect_fibo(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        out: dict[str, pd.Series] = {}
        out.update(self.fibo_swing.apply(df))
        out.update(self.fibo_range.apply(df))
        return out

    def detect_price_action(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        return self.price_action_engine.apply(df)

    def detect_follow_through(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        out: dict[str, pd.Series] = {}
        out.update(PriceActionFollowThrough("bos").apply(df))
        out.update(PriceActionFollowThrough("mss").apply(df))
        return out

    def detect_price_action_liquidity_response(
        self,
        df: pd.DataFrame,
    ) -> dict[str, pd.Series]:
        out: dict[str, pd.Series] = {}

        for src in ("bos", "mss"):
            for side in ("bull", "bear"):
                liq = PriceActionLiquidityResponse(
                    event_source=src,
                    direction=side,
                )
                out.update(liq.apply(df))

        return out

    def calculate_structural_volatility(
        self,
        df: pd.DataFrame,
    ) -> dict[str, pd.Series]:
        out: dict[str, pd.Series] = {}

        for src in ("bos", "mss"):
            for side in ("bull", "bear"):
                sv = PriceActionStructuralVolatility(
                    event_source=src,
                    direction=side,
                )
                out.update(sv.apply(df))

        return out

    def detect_trend_regime(self, df: pd.DataFrame) -> dict[str, pd.Series]:
        return PriceActionTrendRegime().apply(df)










