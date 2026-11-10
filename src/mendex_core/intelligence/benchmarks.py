"""Mendex Engineering Intelligence — Benchmark & Model Evaluation Registry.

Prepares the engineering intelligence architecture for future proprietary model training,
fine-tuning experiments, dataset versioning, and evaluation benchmark tracking.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BenchmarkCase(BaseModel):
    case_id: str
    domain: str  # "magnetics", "circuit_transient", "semiconductor_loss", "drc_safety"
    query_or_input: str
    ground_truth_outputs: Dict[str, float]
    output_units: Dict[str, str]
    allowed_tolerance: float = 0.05  # 5% acceptable error
    reference_solution: str


class EvaluationMetrics(BaseModel):
    total_cases: int
    passed_cases: int
    mean_absolute_error: float
    mean_absolute_percentage_error: float
    accuracy_percentage: float
    all_within_tolerance: bool


class EngineeringBenchmarkRegistry:
    """Benchmark suite for validating engineering reasoning and model accuracy."""

    def __init__(self):
        self._cases: Dict[str, BenchmarkCase] = {}
        self._initialize_benchmark_suite()

    def _initialize_benchmark_suite(self):
        # Benchmark 1: Skin depth at 100 kHz in Copper at 100°C
        self.register_case(BenchmarkCase(
            case_id="BM-SKIN-100KHZ",
            domain="magnetics",
            query_or_input="Copper conductor skin depth at f=100 kHz and T=100°C",
            ground_truth_outputs={"skin_depth_mm": 0.237},
            output_units={"skin_depth_mm": "mm"},
            allowed_tolerance=0.03,
            reference_solution="Analytical solution using rho=2.22e-8 Ohm*m, delta=0.237 mm",
        ))

        # Benchmark 2: Dowell Factor for 2 layers with xi=1.0
        self.register_case(BenchmarkCase(
            case_id="BM-DOWELL-2LAYER",
            domain="magnetics",
            query_or_input="Dowell factor for m=2 layers with h/delta=1.0",
            ground_truth_outputs={"F_R": 1.406},
            output_units={"F_R": "dimensionless"},
            allowed_tolerance=0.05,
            reference_solution="Dowell formula evaluation: F_R = 1.406",
        ))

        # Benchmark 3: LC Resonance for L=10uH, C=100nF
        self.register_case(BenchmarkCase(
            case_id="BM-LC-RESONANCE",
            domain="circuit_transient",
            query_or_input="Resonant frequency for L=10 uH, C=100 nF",
            ground_truth_outputs={"resonant_frequency_hz": 159155.0},
            output_units={"resonant_frequency_hz": "Hz"},
            allowed_tolerance=0.01,
            reference_solution="f_0 = 1 / (2*pi*sqrt(1e-5 * 1e-7)) = 159.155 kHz",
        ))

    def register_case(self, case: BenchmarkCase):
        self._cases[case.case_id] = case

    def get_case(self, case_id: str) -> Optional[BenchmarkCase]:
        return self._cases.get(case_id)

    def list_cases(self, domain: Optional[str] = None) -> List[BenchmarkCase]:
        if domain:
            return [c for c in self._cases.values() if c.domain == domain]
        return list(self._cases.values())

    def evaluate_predictions(
        self,
        predictions: Dict[str, Dict[str, float]],
    ) -> EvaluationMetrics:
        """Evaluates model prediction accuracy against verified engineering benchmarks."""
        total = len(self._cases)
        if total == 0:
            return EvaluationMetrics(
                total_cases=0, passed_cases=0, mean_absolute_error=0.0,
                mean_absolute_percentage_error=0.0, accuracy_percentage=0.0,
                all_within_tolerance=False,
            )

        passed = 0
        total_ape = 0.0
        total_ae = 0.0

        for case_id, case in self._cases.items():
            pred_dict = predictions.get(case_id, {})
            case_passed = True

            for key, target_val in case.ground_truth_outputs.items():
                if key not in pred_dict:
                    case_passed = False
                    total_ape += 1.0  # 100% error if missing
                    continue

                val = pred_dict[key]
                ae = abs(val - target_val)
                ape = ae / abs(target_val) if target_val != 0 else 0.0
                total_ae += ae
                total_ape += ape

                if ape > case.allowed_tolerance:
                    case_passed = False

            if case_passed:
                passed += 1

        mape = (total_ape / total) * 100.0
        mae = total_ae / total
        acc = (passed / total) * 100.0

        return EvaluationMetrics(
            total_cases=total,
            passed_cases=passed,
            mean_absolute_error=mae,
            mean_absolute_percentage_error=mape,
            accuracy_percentage=acc,
            all_within_tolerance=(passed == total),
        )
