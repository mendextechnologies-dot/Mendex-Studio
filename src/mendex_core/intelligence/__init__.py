"""Deterministic engineering knowledge and calculations (no AI model or provider code)."""
from .knowledge import EngineeringKnowledgeService, FormulaRecord, MaterialRecord, StandardProfile
from .calculations import DeterministicCalculationService, CalculationResult
from .benchmarks import EngineeringBenchmarkRegistry, BenchmarkCase, EvaluationMetrics
