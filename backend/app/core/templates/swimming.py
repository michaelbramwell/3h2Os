"""
Swimming plan templates for pool and open water events.

Uses the same periodisation principles as running:
- Base phase: build aerobic endurance, technique focus
- Build phase: increase volume, introduce threshold sets
- Peak phase: race-pace work, maintain volume
- Taper phase: reduce volume, keep sharpness
- Race week: minimal volume, race day

Session structure uses distance + description (no separate sets/reps model).
Set breakdowns are written in the description field.
"""

from .base import (
    PlanTemplateDefinition,
    PhaseDefinition,
    SessionTemplate,
    WeekTemplate,
)


# --- Session building blocks ---

EASY_SWIM = SessionTemplate(
    name_pattern="{distance} Easy Swim",
    activity_type="Swimming",
    workout_format="Easy",
    volume_share=0.20,
    description_pattern="Easy continuous swim. Focus on smooth stroke and breathing rhythm.",
)

TECHNIQUE_SWIM = SessionTemplate(
    name_pattern="{distance} Technique",
    activity_type="Swimming",
    workout_format="Technique",
    volume_share=0.15,
    description_pattern="Drill work: catch-up, fingertip drag, kick sets. Focus on form.",
)

ENDURANCE_SWIM = SessionTemplate(
    name_pattern="{distance} Endurance",
    activity_type="Swimming",
    workout_format="Long",
    volume_share=0.30,
    description_pattern="Long continuous swim at steady pace. Build aerobic base.",
    time_of_day="AM",
)

TEMPO_SWIM = SessionTemplate(
    name_pattern="{distance} Tempo Set",
    activity_type="Swimming",
    workout_format="Tempo",
    volume_share=0.15,
    description_pattern="Sustained effort at CSS pace. E.g. 4-6x400m with 20s rest.",
)

THRESHOLD_SWIM = SessionTemplate(
    name_pattern="{distance} Threshold",
    activity_type="Swimming",
    workout_format="Threshold",
    volume_share=0.12,
    description_pattern="Above CSS pace intervals. E.g. 8-10x200m with 15s rest.",
)

INTERVALS_SWIM = SessionTemplate(
    name_pattern="{distance} Intervals",
    activity_type="Swimming",
    workout_format="Intervals",
    volume_share=0.10,
    description_pattern="High intensity short reps. E.g. 12-16x100m at VO2max pace, 10s rest.",
)

RECOVERY_SWIM = SessionTemplate(
    name_pattern="{distance} Recovery",
    activity_type="Swimming",
    workout_format="Recovery",
    volume_share=0.08,
    description_pattern="Very easy swim with mixed strokes. Active recovery.",
)

# Open water specific
OW_SKILLS_SWIM = SessionTemplate(
    name_pattern="{distance} Open Water Skills",
    activity_type="Swimming",
    workout_format="Technique",
    volume_share=0.15,
    description_pattern="Practice sighting, drafting, beach entries/exits. Navigation drills.",
)

OW_ENDURANCE = SessionTemplate(
    name_pattern="{distance} Open Water Endurance",
    activity_type="Swimming",
    workout_format="Long",
    volume_share=0.30,
    description_pattern="Long open water swim at steady pace. Practice fueling and sighting.",
    time_of_day="AM",
)

RACE_SWIM = SessionTemplate(
    name_pattern="Race Day",
    activity_type="Swimming",
    workout_format="Race",
    volume_share=1.0,
    description_pattern="Race day. Execute your pacing plan.",
)


# --- Phase definitions ---

SWIM_BASE = PhaseDefinition(
    name="base",
    description="Build aerobic endurance and stroke technique.",
    volume_factor=0.55,
    intensity_ratio=0.05,
)

SWIM_BUILD = PhaseDefinition(
    name="build",
    description="Increase volume and introduce threshold work.",
    volume_factor=0.80,
    intensity_ratio=0.15,
)

SWIM_PEAK = PhaseDefinition(
    name="peak",
    description="Race-pace specificity with near-peak volume.",
    volume_factor=0.95,
    intensity_ratio=0.20,
)

SWIM_TAPER = PhaseDefinition(
    name="taper",
    description="Reduce volume, maintain sharpness.",
    volume_factor=0.60,
    intensity_ratio=0.10,
    includes_stepback=False,
)

SWIM_RACE = PhaseDefinition(
    name="race",
    description="Race week. Minimal swimming, stay fresh.",
    volume_factor=0.20,
    intensity_ratio=0.0,
    includes_stepback=False,
)


# --- Pool week templates ---

POOL_BASE_WEEK = WeekTemplate(
    sessions=[
        (0, EASY_SWIM),  # Mon
        (1, TECHNIQUE_SWIM),  # Tue
        (3, EASY_SWIM),  # Thu
        (5, ENDURANCE_SWIM),  # Sat
    ]
)

POOL_BUILD_WEEK = WeekTemplate(
    sessions=[
        (0, EASY_SWIM),  # Mon
        (1, TEMPO_SWIM),  # Tue
        (2, TECHNIQUE_SWIM),  # Wed
        (3, THRESHOLD_SWIM),  # Thu
        (5, ENDURANCE_SWIM),  # Sat
    ]
)

POOL_PEAK_WEEK = WeekTemplate(
    sessions=[
        (0, EASY_SWIM),  # Mon
        (1, INTERVALS_SWIM),  # Tue
        (2, TECHNIQUE_SWIM),  # Wed
        (3, TEMPO_SWIM),  # Thu
        (5, ENDURANCE_SWIM),  # Sat
    ]
)

# --- Advanced pool week templates ---

# Advanced build: intervals + threshold + tempo all present, 6 sessions/week.
POOL_BUILD_WEEK_ADVANCED = WeekTemplate(
    sessions=[
        (0, EASY_SWIM),  # Mon
        (1, INTERVALS_SWIM),  # Tue
        (2, TECHNIQUE_SWIM),  # Wed
        (3, THRESHOLD_SWIM),  # Thu
        (4, TEMPO_SWIM),  # Fri
        (5, ENDURANCE_SWIM),  # Sat
    ]
)

# Advanced peak: intervals + threshold + tempo, endurance maintained, 6 sessions/week.
POOL_PEAK_WEEK_ADVANCED = WeekTemplate(
    sessions=[
        (0, EASY_SWIM),  # Mon
        (1, INTERVALS_SWIM),  # Tue
        (2, RECOVERY_SWIM),  # Wed
        (3, THRESHOLD_SWIM),  # Thu
        (4, TEMPO_SWIM),  # Fri
        (5, ENDURANCE_SWIM),  # Sat
    ]
)


POOL_TAPER_WEEK = WeekTemplate(
    sessions=[
        (0, EASY_SWIM),  # Mon
        (2, TEMPO_SWIM),  # Wed
        (4, RECOVERY_SWIM),  # Fri
    ]
)

POOL_RACE_WEEK = WeekTemplate(
    sessions=[
        (0, EASY_SWIM),  # Mon
        (2, RECOVERY_SWIM),  # Wed
        (6, RACE_SWIM),  # Sun
    ]
)

# --- Open water week templates ---

OW_BASE_WEEK = WeekTemplate(
    sessions=[
        (0, EASY_SWIM),  # Mon (pool)
        (1, TECHNIQUE_SWIM),  # Tue (pool)
        (3, EASY_SWIM),  # Thu (pool)
        (5, OW_ENDURANCE),  # Sat (open water)
    ]
)

OW_BUILD_WEEK = WeekTemplate(
    sessions=[
        (0, EASY_SWIM),  # Mon
        (1, TEMPO_SWIM),  # Tue (pool)
        (2, OW_SKILLS_SWIM),  # Wed (open water skills)
        (3, THRESHOLD_SWIM),  # Thu (pool)
        (5, OW_ENDURANCE),  # Sat (open water)
    ]
)

OW_PEAK_WEEK = WeekTemplate(
    sessions=[
        (0, EASY_SWIM),  # Mon
        (1, INTERVALS_SWIM),  # Tue
        (2, OW_SKILLS_SWIM),  # Wed
        (3, TEMPO_SWIM),  # Thu
        (5, OW_ENDURANCE),  # Sat
    ]
)


# --- Advanced open water week templates ---

# Advanced OW build: intervals + threshold + OW skills, 6 sessions/week.
OW_BUILD_WEEK_ADVANCED = WeekTemplate(
    sessions=[
        (0, EASY_SWIM),  # Mon (pool)
        (1, INTERVALS_SWIM),  # Tue (pool)
        (2, OW_SKILLS_SWIM),  # Wed (open water skills)
        (3, THRESHOLD_SWIM),  # Thu (pool)
        (4, TEMPO_SWIM),  # Fri (pool)
        (5, OW_ENDURANCE),  # Sat (open water)
    ]
)

# Advanced OW peak: all intensity types + OW skills + endurance, 6 sessions/week.
OW_PEAK_WEEK_ADVANCED = WeekTemplate(
    sessions=[
        (0, EASY_SWIM),  # Mon (pool)
        (1, INTERVALS_SWIM),  # Tue (pool)
        (2, OW_SKILLS_SWIM),  # Wed (open water)
        (3, THRESHOLD_SWIM),  # Thu (pool)
        (4, TEMPO_SWIM),  # Fri (pool)
        (5, OW_ENDURANCE),  # Sat (open water)
    ]
)


# ===========================================================================
# POOL TEMPLATES
# ===========================================================================

POOL_1500_BEGINNER = PlanTemplateDefinition(
    sport="swimming",
    event_type="pool_1500m",
    level="beginner",
    default_weeks=14,
    phases=[SWIM_BASE, SWIM_BUILD, SWIM_PEAK, SWIM_TAPER, SWIM_RACE],
    phase_proportions=[0.28, 0.36, 0.14, 0.15, 0.07],
    week_templates={
        "base": POOL_BASE_WEEK,
        "build": POOL_BUILD_WEEK,
        "peak": POOL_PEAK_WEEK,
        "taper": POOL_TAPER_WEEK,
        "race": POOL_RACE_WEEK,
    },
    peak_volume_m=8000,  # 8km peak week
    stepback_frequency=3,
    stepback_factor=0.65,
)

POOL_1500_INTERMEDIATE = PlanTemplateDefinition(
    sport="swimming",
    event_type="pool_1500m",
    level="intermediate",
    default_weeks=14,
    phases=[SWIM_BASE, SWIM_BUILD, SWIM_PEAK, SWIM_TAPER, SWIM_RACE],
    phase_proportions=[0.22, 0.36, 0.14, 0.21, 0.07],
    week_templates={
        "base": POOL_BASE_WEEK,
        "build": POOL_BUILD_WEEK,
        "peak": POOL_PEAK_WEEK,
        "taper": POOL_TAPER_WEEK,
        "race": POOL_RACE_WEEK,
    },
    peak_volume_m=15000,  # 15km peak week
    stepback_frequency=3,
    stepback_factor=0.65,
)

POOL_1500_ADVANCED = PlanTemplateDefinition(
    sport="swimming",
    event_type="pool_1500m",
    level="advanced",
    default_weeks=14,
    phases=[SWIM_BASE, SWIM_BUILD, SWIM_PEAK, SWIM_TAPER, SWIM_RACE],
    phase_proportions=[0.18, 0.40, 0.14, 0.21, 0.07],
    week_templates={
        "base": POOL_BASE_WEEK,
        "build": POOL_BUILD_WEEK_ADVANCED,
        "peak": POOL_PEAK_WEEK_ADVANCED,
        "taper": POOL_TAPER_WEEK,
        "race": POOL_RACE_WEEK,
    },
    peak_volume_m=22000,  # 22km peak week
    stepback_frequency=3,
    stepback_factor=0.70,
)


# ===========================================================================
# OPEN WATER TEMPLATES
# ===========================================================================

OW_5K_BEGINNER = PlanTemplateDefinition(
    sport="swimming",
    event_type="ow_5km",
    level="beginner",
    default_weeks=14,
    phases=[SWIM_BASE, SWIM_BUILD, SWIM_PEAK, SWIM_TAPER, SWIM_RACE],
    phase_proportions=[0.28, 0.36, 0.14, 0.15, 0.07],
    week_templates={
        "base": OW_BASE_WEEK,
        "build": OW_BUILD_WEEK,
        "peak": OW_PEAK_WEEK,
        "taper": POOL_TAPER_WEEK,
        "race": POOL_RACE_WEEK,
    },
    peak_volume_m=12000,  # 12km peak week
    stepback_frequency=3,
    stepback_factor=0.65,
)

OW_5K_INTERMEDIATE = PlanTemplateDefinition(
    sport="swimming",
    event_type="ow_5km",
    level="intermediate",
    default_weeks=14,
    phases=[SWIM_BASE, SWIM_BUILD, SWIM_PEAK, SWIM_TAPER, SWIM_RACE],
    phase_proportions=[0.22, 0.36, 0.14, 0.21, 0.07],
    week_templates={
        "base": OW_BASE_WEEK,
        "build": OW_BUILD_WEEK,
        "peak": OW_PEAK_WEEK,
        "taper": POOL_TAPER_WEEK,
        "race": POOL_RACE_WEEK,
    },
    peak_volume_m=20000,  # 20km peak week
    stepback_frequency=3,
    stepback_factor=0.65,
)

OW_5K_ADVANCED = PlanTemplateDefinition(
    sport="swimming",
    event_type="ow_5km",
    level="advanced",
    default_weeks=14,
    phases=[SWIM_BASE, SWIM_BUILD, SWIM_PEAK, SWIM_TAPER, SWIM_RACE],
    phase_proportions=[0.18, 0.40, 0.14, 0.21, 0.07],
    week_templates={
        "base": OW_BASE_WEEK,
        "build": OW_BUILD_WEEK_ADVANCED,
        "peak": OW_PEAK_WEEK_ADVANCED,
        "taper": POOL_TAPER_WEEK,
        "race": POOL_RACE_WEEK,
    },
    peak_volume_m=28000,  # 28km peak week
    stepback_frequency=3,
    stepback_factor=0.70,
)


# ===========================================================================
# TEMPLATE REGISTRY
# ===========================================================================

SWIMMING_TEMPLATES: dict[tuple[str, str], PlanTemplateDefinition] = {
    # Pool events
    ("pool_400m", "beginner"): POOL_1500_BEGINNER,  # Scale down from 1500 template
    ("pool_400m", "intermediate"): POOL_1500_INTERMEDIATE,
    ("pool_400m", "advanced"): POOL_1500_ADVANCED,
    ("pool_800m", "beginner"): POOL_1500_BEGINNER,
    ("pool_800m", "intermediate"): POOL_1500_INTERMEDIATE,
    ("pool_800m", "advanced"): POOL_1500_ADVANCED,
    ("pool_1500m", "beginner"): POOL_1500_BEGINNER,
    ("pool_1500m", "intermediate"): POOL_1500_INTERMEDIATE,
    ("pool_1500m", "advanced"): POOL_1500_ADVANCED,
    # Open water events
    ("ow_1km", "beginner"): OW_5K_BEGINNER,
    ("ow_1km", "intermediate"): OW_5K_INTERMEDIATE,
    ("ow_1km", "advanced"): OW_5K_ADVANCED,
    ("ow_2.5km", "beginner"): OW_5K_BEGINNER,
    ("ow_2.5km", "intermediate"): OW_5K_INTERMEDIATE,
    ("ow_2.5km", "advanced"): OW_5K_ADVANCED,
    ("ow_5km", "beginner"): OW_5K_BEGINNER,
    ("ow_5km", "intermediate"): OW_5K_INTERMEDIATE,
    ("ow_5km", "advanced"): OW_5K_ADVANCED,
    ("ow_10km", "beginner"): OW_5K_BEGINNER,
    ("ow_10km", "intermediate"): OW_5K_INTERMEDIATE,
    ("ow_10km", "advanced"): OW_5K_ADVANCED,
}
