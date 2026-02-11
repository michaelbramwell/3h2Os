"""
Running plan templates for all event types and experience levels.

Templates are built from established sports science principles:
- Base phase: aerobic foundation, gradual volume build
- Build phase: introduce intensity (tempo, intervals, threshold)
- Peak phase: maintain volume, sharpen with race-specific work
- Taper phase: reduce volume, maintain intensity
- Race week: minimal volume, race day
"""

from .base import (
    PlanTemplateDefinition,
    PhaseDefinition,
    SessionTemplate,
    WeekTemplate,
)


# --- Session building blocks ---

# Easy / Recovery sessions
EASY_RUN = SessionTemplate(
    name_pattern="{distance} Easy Run",
    activity_type="Run",
    workout_format="Easy",
    volume_share=0.20,
    description_pattern="Easy pace, conversational effort. Stay in Zone 2.",
)

RECOVERY_RUN = SessionTemplate(
    name_pattern="{distance} Recovery",
    activity_type="Run",
    workout_format="Recovery",
    volume_share=0.10,
    description_pattern="Very easy recovery jog. Keep heart rate in Zone 1.",
)

# Long run
LONG_RUN = SessionTemplate(
    name_pattern="{distance} SLR",
    activity_type="Run",
    workout_format="Long",
    volume_share=0.30,
    description_pattern="Sunday long run at easy pace. Practice fueling strategy.",
    time_of_day="AM",
)

LONG_RUN_PROGRESSION = SessionTemplate(
    name_pattern="{distance} Progression SLR",
    activity_type="Run",
    workout_format="Progression",
    volume_share=0.30,
    description_pattern="Sunday long run. Start easy, build to tempo pace in final third.",
    time_of_day="AM",
)

# Intensity sessions
TEMPO_RUN = SessionTemplate(
    name_pattern="{distance} Tempo",
    activity_type="Run",
    workout_format="Tempo",
    volume_share=0.15,
    description_pattern="Sustained effort at tempo pace (Zone 3). Comfortably hard.",
)

THRESHOLD_RUN = SessionTemplate(
    name_pattern="{distance} Threshold",
    activity_type="Run",
    workout_format="Threshold",
    volume_share=0.12,
    description_pattern="Threshold pace intervals (Zone 4). Hard but controlled.",
)

INTERVALS = SessionTemplate(
    name_pattern="{distance} Intervals",
    activity_type="Run",
    workout_format="Intervals",
    volume_share=0.10,
    description_pattern="High intensity intervals with recovery jog between reps.",
)

FARTLEK = SessionTemplate(
    name_pattern="{distance} Fartlek",
    activity_type="Run",
    workout_format="Fartlek",
    volume_share=0.15,
    description_pattern="Unstructured speed play. Mix fast and easy efforts by feel.",
)

HILLS = SessionTemplate(
    name_pattern="{distance} Hills",
    activity_type="Run",
    workout_format="Hills",
    volume_share=0.12,
    description_pattern="Hill repeats or hilly route. Build strength and running economy.",
)

STEADY_RUN = SessionTemplate(
    name_pattern="{distance} Steady Run",
    activity_type="Run",
    workout_format="Steady",
    volume_share=0.18,
    description_pattern="Steady effort between easy and tempo. Zone 2-3 boundary.",
)

# Race day
RACE_SESSION = SessionTemplate(
    name_pattern="Race Day",
    activity_type="Run",
    workout_format="Race",
    volume_share=1.0,
    description_pattern="Race day. Execute your plan.",
)


# --- Phase definitions ---

BASE_PHASE = PhaseDefinition(
    name="base",
    description="Build aerobic foundation with easy running and gradual volume increase.",
    volume_factor=0.55,
    intensity_ratio=0.05,
)

BUILD_PHASE = PhaseDefinition(
    name="build",
    description="Progressive overload with increasing volume and intensity work.",
    volume_factor=0.80,
    intensity_ratio=0.15,
)

PEAK_PHASE = PhaseDefinition(
    name="peak",
    description="Near-peak volume with race-specific intensity. Sharpening phase.",
    volume_factor=0.95,
    intensity_ratio=0.20,
)

TAPER_PHASE = PhaseDefinition(
    name="taper",
    description="Reduce volume while maintaining some intensity. Fresh legs for race day.",
    volume_factor=0.60,
    intensity_ratio=0.15,
    includes_stepback=False,
)

RACE_PHASE = PhaseDefinition(
    name="race",
    description="Race week. Minimal volume, stay sharp.",
    volume_factor=0.25,
    intensity_ratio=0.0,
    includes_stepback=False,
)


# --- Week templates ---

# Base phase: mostly easy running with one longer run
BASE_WEEK = WeekTemplate(
    sessions=[
        (0, EASY_RUN),  # Mon
        (1, RECOVERY_RUN),  # Tue
        (2, EASY_RUN),  # Wed
        (3, STEADY_RUN),  # Thu
        (4, RECOVERY_RUN),  # Fri
        (6, LONG_RUN),  # Sun
    ]
)

# Build phase: introduce quality sessions
BUILD_WEEK = WeekTemplate(
    sessions=[
        (0, EASY_RUN),  # Mon
        (1, TEMPO_RUN),  # Tue
        (2, EASY_RUN),  # Wed
        (3, THRESHOLD_RUN),  # Thu
        (4, RECOVERY_RUN),  # Fri
        (6, LONG_RUN),  # Sun
    ]
)

# Peak phase: race-specific sharpening
PEAK_WEEK = WeekTemplate(
    sessions=[
        (0, EASY_RUN),  # Mon
        (1, INTERVALS),  # Tue
        (2, EASY_RUN),  # Wed
        (3, TEMPO_RUN),  # Thu
        (4, RECOVERY_RUN),  # Fri
        (6, LONG_RUN_PROGRESSION),  # Sun
    ]
)

# Taper phase: reduced volume, some sharpness.
# Used by shorter events (5K, 10K) where a single taper style is sufficient.
TAPER_WEEK = WeekTemplate(
    sessions=[
        (0, EASY_RUN),  # Mon
        (1, TEMPO_RUN),  # Tue
        (2, RECOVERY_RUN),  # Wed
        (3, EASY_RUN),  # Thu
        (6, EASY_RUN),  # Sun (shorter run)
    ]
)

# Distance-event taper (half marathon, marathon, ultra):
# Early taper keeps a reduced-volume long run on Sunday to maintain endurance.
TAPER_WEEK_EARLY = WeekTemplate(
    sessions=[
        (0, EASY_RUN),  # Mon
        (1, TEMPO_RUN),  # Tue
        (2, RECOVERY_RUN),  # Wed
        (3, EASY_RUN),  # Thu
        (6, LONG_RUN),  # Sun (reduced-volume long run)
    ]
)

# Late taper: drop the long run entirely, reduce session count, all easy/recovery.
TAPER_WEEK_LATE = WeekTemplate(
    sessions=[
        (0, EASY_RUN),  # Mon
        (1, EASY_RUN),  # Tue
        (3, RECOVERY_RUN),  # Thu
        (6, EASY_RUN),  # Sun (short shakeout)
    ]
)

# Race week: minimal
RACE_WEEK = WeekTemplate(
    sessions=[
        (0, EASY_RUN),  # Mon
        (2, RECOVERY_RUN),  # Wed
        (4, RECOVERY_RUN),  # Fri
        (6, RACE_SESSION),  # Sun
    ]
)


# --- Beginner variants ---

BASE_WEEK_BEGINNER = WeekTemplate(
    sessions=[
        (1, EASY_RUN),  # Tue
        (3, EASY_RUN),  # Thu
        (6, LONG_RUN),  # Sun
    ]
)

BUILD_WEEK_BEGINNER = WeekTemplate(
    sessions=[
        (1, EASY_RUN),  # Tue
        (3, FARTLEK),  # Thu
        (6, LONG_RUN),  # Sun
        (0, RECOVERY_RUN),  # Mon (optional 4th day)
    ]
)

PEAK_WEEK_BEGINNER = WeekTemplate(
    sessions=[
        (1, TEMPO_RUN),  # Tue
        (3, EASY_RUN),  # Thu
        (6, LONG_RUN),  # Sun
        (0, RECOVERY_RUN),  # Mon (optional)
    ]
)


# --- Advanced variants ---

# Advanced build: both interval AND threshold intensity each week, progression SLR.
# Used by marathon, half marathon, and ultra advanced plans.
BUILD_WEEK_ADVANCED = WeekTemplate(
    sessions=[
        (0, EASY_RUN),  # Mon
        (1, INTERVALS),  # Tue
        (2, EASY_RUN),  # Wed
        (3, THRESHOLD_RUN),  # Thu
        (4, RECOVERY_RUN),  # Fri
        (6, LONG_RUN_PROGRESSION),  # Sun
    ]
)

# Advanced peak: intervals + threshold + tempo all present, progression SLR.
PEAK_WEEK_ADVANCED = WeekTemplate(
    sessions=[
        (0, EASY_RUN),  # Mon
        (1, INTERVALS),  # Tue
        (2, RECOVERY_RUN),  # Wed
        (3, THRESHOLD_RUN),  # Thu
        (4, TEMPO_RUN),  # Fri
        (6, LONG_RUN_PROGRESSION),  # Sun
    ]
)

# Advanced 5K/10K peak: same intensity spread as distance advanced peak,
# but steady run on Sunday instead of progression SLR (short-event focus).
PEAK_WEEK_5K_ADVANCED = WeekTemplate(
    sessions=[
        (0, EASY_RUN),  # Mon
        (1, INTERVALS),  # Tue
        (2, RECOVERY_RUN),  # Wed
        (3, THRESHOLD_RUN),  # Thu
        (4, TEMPO_RUN),  # Fri
        (6, STEADY_RUN),  # Sun
    ]
)


# ===========================================================================
# MARATHON TEMPLATES
# ===========================================================================

MARATHON_BEGINNER = PlanTemplateDefinition(
    sport="running",
    event_type="marathon",
    level="beginner",
    default_weeks=14,
    phases=[BASE_PHASE, BUILD_PHASE, PEAK_PHASE, TAPER_PHASE, RACE_PHASE],
    phase_proportions=[0.28, 0.36, 0.14, 0.15, 0.07],
    week_templates={
        "base": BASE_WEEK_BEGINNER,
        "build": BUILD_WEEK_BEGINNER,
        "peak": PEAK_WEEK_BEGINNER,
        "taper": [TAPER_WEEK_EARLY, TAPER_WEEK_LATE],
        "race": RACE_WEEK,
    },
    peak_volume_m=50000,  # 50km peak week
    stepback_frequency=3,
    stepback_factor=0.65,
)

MARATHON_INTERMEDIATE = PlanTemplateDefinition(
    sport="running",
    event_type="marathon",
    level="intermediate",
    default_weeks=14,
    phases=[BASE_PHASE, BUILD_PHASE, PEAK_PHASE, TAPER_PHASE, RACE_PHASE],
    phase_proportions=[0.22, 0.36, 0.14, 0.21, 0.07],
    week_templates={
        "base": BASE_WEEK,
        "build": BUILD_WEEK,
        "peak": PEAK_WEEK,
        "taper": [TAPER_WEEK_EARLY, TAPER_WEEK_LATE],
        "race": RACE_WEEK,
    },
    peak_volume_m=85000,  # 85km peak week
    stepback_frequency=3,
    stepback_factor=0.65,
)

MARATHON_ADVANCED = PlanTemplateDefinition(
    sport="running",
    event_type="marathon",
    level="advanced",
    default_weeks=14,
    phases=[BASE_PHASE, BUILD_PHASE, PEAK_PHASE, TAPER_PHASE, RACE_PHASE],
    phase_proportions=[0.18, 0.40, 0.14, 0.21, 0.07],
    week_templates={
        "base": BASE_WEEK,
        "build": BUILD_WEEK_ADVANCED,
        "peak": PEAK_WEEK_ADVANCED,
        "taper": [TAPER_WEEK_EARLY, TAPER_WEEK_LATE],
        "race": RACE_WEEK,
    },
    peak_volume_m=130000,  # 130km peak week
    stepback_frequency=3,
    stepback_factor=0.65,
)


# ===========================================================================
# HALF MARATHON TEMPLATES
# ===========================================================================

HALF_BEGINNER = PlanTemplateDefinition(
    sport="running",
    event_type="half_marathon",
    level="beginner",
    default_weeks=14,
    phases=[BASE_PHASE, BUILD_PHASE, PEAK_PHASE, TAPER_PHASE, RACE_PHASE],
    phase_proportions=[0.28, 0.36, 0.14, 0.15, 0.07],
    week_templates={
        "base": BASE_WEEK_BEGINNER,
        "build": BUILD_WEEK_BEGINNER,
        "peak": PEAK_WEEK_BEGINNER,
        "taper": [TAPER_WEEK_EARLY, TAPER_WEEK_LATE],
        "race": RACE_WEEK,
    },
    peak_volume_m=40000,  # 40km peak week
    stepback_frequency=3,
    stepback_factor=0.65,
)

HALF_INTERMEDIATE = PlanTemplateDefinition(
    sport="running",
    event_type="half_marathon",
    level="intermediate",
    default_weeks=14,
    phases=[BASE_PHASE, BUILD_PHASE, PEAK_PHASE, TAPER_PHASE, RACE_PHASE],
    phase_proportions=[0.22, 0.36, 0.14, 0.21, 0.07],
    week_templates={
        "base": BASE_WEEK,
        "build": BUILD_WEEK,
        "peak": PEAK_WEEK,
        "taper": [TAPER_WEEK_EARLY, TAPER_WEEK_LATE],
        "race": RACE_WEEK,
    },
    peak_volume_m=55000,  # 55km peak week
    stepback_frequency=3,
    stepback_factor=0.65,
)

HALF_ADVANCED = PlanTemplateDefinition(
    sport="running",
    event_type="half_marathon",
    level="advanced",
    default_weeks=14,
    phases=[BASE_PHASE, BUILD_PHASE, PEAK_PHASE, TAPER_PHASE, RACE_PHASE],
    phase_proportions=[0.18, 0.40, 0.14, 0.21, 0.07],
    week_templates={
        "base": BASE_WEEK,
        "build": BUILD_WEEK_ADVANCED,
        "peak": PEAK_WEEK_ADVANCED,
        "taper": [TAPER_WEEK_EARLY, TAPER_WEEK_LATE],
        "race": RACE_WEEK,
    },
    peak_volume_m=70000,  # 70km peak week
    stepback_frequency=3,
    stepback_factor=0.65,
)


# ===========================================================================
# 5K TEMPLATES
# ===========================================================================

# 5K has more intensity focus, shorter long runs relative to volume
BUILD_WEEK_5K = WeekTemplate(
    sessions=[
        (0, EASY_RUN),  # Mon
        (1, INTERVALS),  # Tue
        (2, EASY_RUN),  # Wed
        (3, TEMPO_RUN),  # Thu
        (4, RECOVERY_RUN),  # Fri
        (6, LONG_RUN),  # Sun
    ]
)

PEAK_WEEK_5K = WeekTemplate(
    sessions=[
        (0, EASY_RUN),  # Mon
        (1, INTERVALS),  # Tue
        (2, RECOVERY_RUN),  # Wed
        (3, THRESHOLD_RUN),  # Thu
        (4, RECOVERY_RUN),  # Fri
        (6, STEADY_RUN),  # Sun
    ]
)

FIVE_K_BEGINNER = PlanTemplateDefinition(
    sport="running",
    event_type="5k",
    level="beginner",
    default_weeks=14,
    phases=[BASE_PHASE, BUILD_PHASE, PEAK_PHASE, TAPER_PHASE, RACE_PHASE],
    phase_proportions=[0.35, 0.30, 0.14, 0.14, 0.07],
    week_templates={
        "base": BASE_WEEK_BEGINNER,
        "build": BUILD_WEEK_BEGINNER,
        "peak": PEAK_WEEK_BEGINNER,
        "taper": TAPER_WEEK,
        "race": RACE_WEEK,
    },
    peak_volume_m=25000,  # 25km peak week
    stepback_frequency=3,
    stepback_factor=0.65,
)

FIVE_K_INTERMEDIATE = PlanTemplateDefinition(
    sport="running",
    event_type="5k",
    level="intermediate",
    default_weeks=14,
    phases=[BASE_PHASE, BUILD_PHASE, PEAK_PHASE, TAPER_PHASE, RACE_PHASE],
    phase_proportions=[0.22, 0.36, 0.14, 0.21, 0.07],
    week_templates={
        "base": BASE_WEEK,
        "build": BUILD_WEEK_5K,
        "peak": PEAK_WEEK_5K,
        "taper": TAPER_WEEK,
        "race": RACE_WEEK,
    },
    peak_volume_m=40000,  # 40km peak week
    stepback_frequency=3,
    stepback_factor=0.65,
)

FIVE_K_ADVANCED = PlanTemplateDefinition(
    sport="running",
    event_type="5k",
    level="advanced",
    default_weeks=14,
    phases=[BASE_PHASE, BUILD_PHASE, PEAK_PHASE, TAPER_PHASE, RACE_PHASE],
    phase_proportions=[0.18, 0.40, 0.14, 0.21, 0.07],
    week_templates={
        "base": BASE_WEEK,
        "build": BUILD_WEEK_ADVANCED,
        "peak": PEAK_WEEK_5K_ADVANCED,
        "taper": TAPER_WEEK,
        "race": RACE_WEEK,
    },
    peak_volume_m=50000,  # 50km peak week
    stepback_frequency=3,
    stepback_factor=0.65,
)


# ===========================================================================
# 10K TEMPLATES
# ===========================================================================

TEN_K_BEGINNER = PlanTemplateDefinition(
    sport="running",
    event_type="10k",
    level="beginner",
    default_weeks=14,
    phases=[BASE_PHASE, BUILD_PHASE, PEAK_PHASE, TAPER_PHASE, RACE_PHASE],
    phase_proportions=[0.28, 0.36, 0.14, 0.15, 0.07],
    week_templates={
        "base": BASE_WEEK_BEGINNER,
        "build": BUILD_WEEK_BEGINNER,
        "peak": PEAK_WEEK_BEGINNER,
        "taper": TAPER_WEEK,
        "race": RACE_WEEK,
    },
    peak_volume_m=35000,  # 35km peak week
    stepback_frequency=3,
    stepback_factor=0.65,
)

TEN_K_INTERMEDIATE = PlanTemplateDefinition(
    sport="running",
    event_type="10k",
    level="intermediate",
    default_weeks=14,
    phases=[BASE_PHASE, BUILD_PHASE, PEAK_PHASE, TAPER_PHASE, RACE_PHASE],
    phase_proportions=[0.22, 0.36, 0.14, 0.21, 0.07],
    week_templates={
        "base": BASE_WEEK,
        "build": BUILD_WEEK_5K,  # Similar intensity profile to 5K
        "peak": PEAK_WEEK_5K,
        "taper": TAPER_WEEK,
        "race": RACE_WEEK,
    },
    peak_volume_m=50000,  # 50km peak week
    stepback_frequency=3,
    stepback_factor=0.65,
)

TEN_K_ADVANCED = PlanTemplateDefinition(
    sport="running",
    event_type="10k",
    level="advanced",
    default_weeks=14,
    phases=[BASE_PHASE, BUILD_PHASE, PEAK_PHASE, TAPER_PHASE, RACE_PHASE],
    phase_proportions=[0.18, 0.40, 0.14, 0.21, 0.07],
    week_templates={
        "base": BASE_WEEK,
        "build": BUILD_WEEK_ADVANCED,
        "peak": PEAK_WEEK_5K_ADVANCED,
        "taper": TAPER_WEEK,
        "race": RACE_WEEK,
    },
    peak_volume_m=60000,  # 60km peak week
    stepback_frequency=3,
    stepback_factor=0.65,
)


# ===========================================================================
# ULTRA TEMPLATE (50K baseline)
# ===========================================================================

ULTRA_INTERMEDIATE = PlanTemplateDefinition(
    sport="running",
    event_type="ultra",
    level="intermediate",
    default_weeks=14,
    phases=[BASE_PHASE, BUILD_PHASE, PEAK_PHASE, TAPER_PHASE, RACE_PHASE],
    phase_proportions=[0.22, 0.36, 0.14, 0.21, 0.07],
    week_templates={
        "base": BASE_WEEK,
        "build": BUILD_WEEK,
        "peak": PEAK_WEEK,
        "taper": [TAPER_WEEK_EARLY, TAPER_WEEK_LATE],
        "race": RACE_WEEK,
    },
    peak_volume_m=90000,  # 90km peak week
    stepback_frequency=3,
    stepback_factor=0.65,
)

ULTRA_ADVANCED = PlanTemplateDefinition(
    sport="running",
    event_type="ultra",
    level="advanced",
    default_weeks=14,
    phases=[BASE_PHASE, BUILD_PHASE, PEAK_PHASE, TAPER_PHASE, RACE_PHASE],
    phase_proportions=[0.18, 0.40, 0.14, 0.21, 0.07],
    week_templates={
        "base": BASE_WEEK,
        "build": BUILD_WEEK_ADVANCED,
        "peak": PEAK_WEEK_ADVANCED,
        "taper": [TAPER_WEEK_EARLY, TAPER_WEEK_LATE],
        "race": RACE_WEEK,
    },
    peak_volume_m=120000,  # 120km peak week
    stepback_frequency=3,
    stepback_factor=0.65,
)


# ===========================================================================
# TEMPLATE REGISTRY
# ===========================================================================

RUNNING_TEMPLATES: dict[tuple[str, str], PlanTemplateDefinition] = {
    ("5k", "beginner"): FIVE_K_BEGINNER,
    ("5k", "intermediate"): FIVE_K_INTERMEDIATE,
    ("5k", "advanced"): FIVE_K_ADVANCED,
    ("10k", "beginner"): TEN_K_BEGINNER,
    ("10k", "intermediate"): TEN_K_INTERMEDIATE,
    ("10k", "advanced"): TEN_K_ADVANCED,
    ("half_marathon", "beginner"): HALF_BEGINNER,
    ("half_marathon", "intermediate"): HALF_INTERMEDIATE,
    ("half_marathon", "advanced"): HALF_ADVANCED,
    ("marathon", "beginner"): MARATHON_BEGINNER,
    ("marathon", "intermediate"): MARATHON_INTERMEDIATE,
    ("marathon", "advanced"): MARATHON_ADVANCED,
    ("ultra", "beginner"): ULTRA_INTERMEDIATE,  # Fallback: no beginner ultra
    ("ultra", "intermediate"): ULTRA_INTERMEDIATE,
    ("ultra", "advanced"): ULTRA_ADVANCED,
}
