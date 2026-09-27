"""
NEP Excellence Awards 2026 - College Parameter Evaluators (C1–C22)

All College parameters are evaluated by the shared, definition-driven pipeline in
apps.scoring.rules.common (rules in apps.scoring.rules.definitions, inputs in apps.scoring.field_schema).
"""
from typing import Callable, Dict

from apps.scoring.domain import AssessmentContext, ParameterInput, ParameterResult
from apps.scoring.evaluators.double_counting import DoubleCountingValidator

from .common import build_evaluators
from .definitions import COLLEGE_PARAMETERS

COLLEGE_EVALUATORS: Dict[str, Callable[[ParameterInput, AssessmentContext, DoubleCountingValidator], ParameterResult]] = (
    build_evaluators(COLLEGE_PARAMETERS)
)
