"""
NEP Excellence Awards 2026 - Parameter Rule Definitions and Evaluators
"""
from .definitions import UNIVERSITY_PARAMETERS, COLLEGE_PARAMETERS
from .university import UNIVERSITY_EVALUATORS
from .college import COLLEGE_EVALUATORS

__all__ = [
    "UNIVERSITY_PARAMETERS",
    "COLLEGE_PARAMETERS",
    "UNIVERSITY_EVALUATORS",
    "COLLEGE_EVALUATORS",
]
