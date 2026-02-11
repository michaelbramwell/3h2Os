"""
Template engine for generating periodised training plans.

Plan templates are built from generic sports science principles:
- Periodisation phases (base, build, peak, taper, race)
- 80/20 intensity distribution
- Progressive overload (7% build per week)
- Step-back recovery weeks (every 3-4 weeks, 65% volume)
- Taper protocol (60% volume reduction)
"""

from .base import generate_plan_from_template, calculate_phase_structure
from .running import RUNNING_TEMPLATES
from .swimming import SWIMMING_TEMPLATES

__all__ = [
    "generate_plan_from_template",
    "calculate_phase_structure",
    "RUNNING_TEMPLATES",
    "SWIMMING_TEMPLATES",
]
