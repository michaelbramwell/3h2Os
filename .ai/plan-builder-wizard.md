# Plan Builder Wizard -- Design Document

**Status**: Planning
**Date**: 2026-02-09

---

## Overview

Add a multi-step wizard interface for creating structured training plans for both running and swimming. Currently, `CreatePlanDialog` is a bare-bones modal (title + type only) that creates an empty plan. The wizard replaces this with a guided flow that collects enough information to generate a complete, periodised training plan.

---

## Wizard Steps

### Step 1: Sport & Event

- **Sport type**: Running / Swimming
- **Event selection** (dynamic based on sport):
  - Running: 5K, 10K, Half Marathon, Marathon, Ultra
  - Swimming (Pool): 400m, 800m, 1500m
  - Swimming (Open Water): 1km, 2.5km, 5km, 10km
- **Event date** (optional but recommended -- drives periodisation)
- **Event name** (free text, e.g. "Perth City to Surf 2026")

### Step 2: Athlete Profile

- **Experience level**: Beginner, Intermediate, Advanced
- **Age** (integer)
- **Weight** (kg, used for fueling/pacing estimates)
- **Events completed**: How many times they have completed the target event distance (0, 1-3, 4-10, 10+). Stored per event type on the user profile.
- **Training zones**:
  - Beginner: Auto-calculated from age/weight using standard formulas (displayed read-only, no input needed)
  - Intermediate / Advanced: Option to accept pre-calculated zones OR enter custom values (HR zones, pace zones, swim CSS)
- Note: This data syncs back to `RunnerProfile` so it persists across plans (user-scoped).

### Step 3: Goals & Focus

- **Primary goal** (single select):
  - Finish / Complete the distance
  - PB / Faster time
  - Specific time target (sub-3, sub-4, etc. -- free text input shown when selected)
  - Consistency / Build base
  - Enjoyment / Injury-free
- **Pain points** (multi-select):
  - Cramping
  - Bonking / Energy management
  - Pacing (going out too fast)
  - Injury recurrence
  - Mental fatigue / Motivation
  - Recovery between sessions
  - Speed in final third
  - Breathing / VO2 ceiling
  - Open water anxiety (swimming only)
  - Stroke efficiency (swimming only)
- **Weekly availability**: How many days per week they can train (3-7 slider or select)
- **Longest recent session**: Approximate current longest run/swim distance (helps set starting volume)

### Step 4: Plan Generation Method

Two modes (this is the key architectural decision -- see section below):

- **Template-based** (default, free): Select from proven, hardcoded periodisation formulas. Deterministic output. Adjustable after generation.
- **AI-assisted** (premium, future): AI generates a bespoke plan using the collected inputs, constrained by the existing validation engine guardrails. Non-deterministic but reviewed before saving.

### Step 5: Review & Confirm

- Preview of the generated plan skeleton: week count, phase breakdown (base, build, peak, taper, race), weekly volume curve chart.
- Option to adjust total weeks, start date, peak week volume.
- "Create Plan" button commits to DB.

---

## Clone Existing Plan

Separate from the wizard but complementary:

- From `PlanSwitcher`, add a "Clone" action on any existing plan.
- Clones all weeks and workouts into a new plan with a new title (e.g. "Marathon Plan (copy)").
- User can then adjust dates, volumes, etc. after cloning.
- Backend: `POST /api/plans/{id}/clone` -- copies `RunnerPlan` + `PlanWeek` + `PlanWorkout` rows with new IDs and shifted dates.

---

## Key Decision: Template vs AI Plan Generation

### Option A: Template-Based (Hardcoded Formulas)

Proven periodisation structures encoded as Python logic. Given the inputs (event, level, weeks available, weekly sessions, goal), the system selects a template and parameterises it.

**How it works**:
- A library of plan templates per event type and level (e.g. `marathon_beginner`, `5k_intermediate`).
- Each template defines: phase structure (base/build/peak/taper), session types per day, volume progression curve (percentages of peak volume), key workout prescriptions.
- Templates are custom-designed from established sports science principles: periodisation phases, 80/20 intensity distribution, progressive overload, step-back recovery weeks. No proprietary methodology -- just sound, generic coaching principles.
- The wizard inputs parameterise the template: total weeks (default 14, user-adjustable), peak volume, long run cap, intensity ratio, session count, start/end dates.
- Output is deterministic -- same inputs always produce the same plan.

**Pros**:
- Reliable, tested, no hallucination risk.
- No API cost.
- Fully offline capable.
- Easy to unit test.
- Respects existing validation engine naturally (templates are designed within the rules).

**Cons**:
- Limited flexibility -- plans feel "cookie cutter" for advanced users.
- Maintenance burden as more event types / levels are added.
- Cannot easily account for nuanced pain points or unusual constraints.

### Option B: AI-Assisted Generation (Guardrailed)

LLM generates a plan given a structured prompt built from wizard inputs, constrained by strict output schema and validated against the existing validation engine before saving.

**How it works**:
- Wizard inputs are assembled into a structured prompt with explicit constraints (max volume progression 15%, intensity cap 25%, long run cap 40%, etc.).
- LLM returns a JSON plan conforming to the existing `WeekSchema`/`WorkoutSchema` structure.
- Backend validates the generated plan through the same `validation.py` engine before persisting.
- If validation fails, the system either retries with feedback or flags issues for user review.

**Pros**:
- Highly personalised plans that account for pain points, goals, and edge cases.
- Scales to new event types without manual template authoring.
- Natural upsell path for a premium tier.

**Cons**:
- API cost per generation.
- Non-deterministic -- harder to test, potential for odd plans.
- Requires robust output parsing and validation.
- Latency (5-15 seconds to generate).
- Dependency on external service availability.

### Recommendation: Both (Phased)

**Phase 1**: Template-based only. Build the wizard UI, the template engine, and the clone feature. This gives immediate value with zero risk.

**Phase 2**: AI-assisted as an opt-in alternative. The wizard adds a toggle: "Use AI to customise this plan". The AI path uses the same wizard inputs but routes through the LLM pipeline instead of the template engine. The validation engine acts as the guardrail -- no plan saves without passing the same rules. This becomes the premium/paid feature.

The wizard UI is identical for both paths -- only the generation backend differs. This means Phase 1 work is not throwaway.

---

## Data Model Changes

### New Fields on `RunnerProfile`

```
experience_level: str              # "beginner" | "intermediate" | "advanced"
events_completed_json: str         # JSON map, e.g. {"marathon": 3, "half_marathon": 5}
pain_points_json: str              # JSON array of pain point tags
weekly_availability: int           # days per week available to train
longest_recent_distance_m: int     # current longest session in metres
```

### New Fields on `RunnerProject`

```
event_type: str        # "5k" | "10k" | "half_marathon" | "marathon" | "ultra" | etc.
target_time: str       # nullable, e.g. "3:45:00"
primary_goal: str      # "finish" | "pb" | "target_time" | "consistency" | "enjoyment"
```

### New Table: `PlanTemplate`

```
id: int
sport: str             # "running" | "swimming"
event_type: str        # "marathon" | "5k" | etc.
level: str             # "beginner" | "intermediate" | "advanced"
default_weeks: int     # default plan length (14 typical), user can override
structure_json: str    # JSON blob defining phases, session patterns, volume curve
```

### Migration

Single Alembic migration adding the new columns (nullable, with defaults) and the `PlanTemplate` table. No breaking changes to existing data.

---

## Backend Architecture

```
backend/app/
  services/
    plan_builder.py        # New -- orchestrates plan generation
  core/
    templates/
      __init__.py
      running.py           # Running plan templates
      swimming.py          # Swimming plan templates
      base.py              # Shared template logic (periodisation, volume curves)
    ai_generator.py        # Phase 2 -- LLM plan generation with guardrails
  schemas.py               # New DTOs: WizardStepSchemas, PlanPreview
  routers/
    api.py                 # New endpoints: POST /api/plans/generate-preview,
                           #                POST /api/plans/from-wizard,
                           #                POST /api/plans/{id}/clone
```

### New Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/plans/generate-preview` | Takes wizard inputs, returns plan preview (phases, volume curve) without saving |
| `POST` | `/api/plans/from-wizard` | Takes wizard inputs, generates and saves the full plan |
| `POST` | `/api/plans/{id}/clone` | Clones an existing plan with new dates |

---

## Frontend Architecture

```
frontend/src/
  components/
    wizard/
      PlanWizard.tsx          # Main wizard container (step state machine)
      StepSportEvent.tsx      # Step 1
      StepAthleteProfile.tsx  # Step 2
      StepGoalsFocus.tsx      # Step 3
      StepGenerationMethod.tsx # Step 4
      StepReviewConfirm.tsx   # Step 5
      WizardProgress.tsx      # Step indicator bar
    ClonePlanDialog.tsx       # Clone flow (title + date offset)
  hooks/
    useWizard.ts              # Step navigation, form state accumulation
  types/
    wizard.ts                 # TypeScript types for wizard state
```

The wizard does not need its own route. It can be a full-screen dialog/modal launched from the existing dashboard, keeping the single-route architecture.

---

## Implementation Phases

### Phase 1: Foundation (Template-Based Plans)

1. Database migration (new columns + `PlanTemplate` table)
2. Template engine (`core/templates/`) with at least:
   - Marathon: beginner, intermediate, advanced (14 week default, variable)
   - Half marathon: beginner, intermediate (14 week default, variable)
   - 5K: beginner, intermediate (14 week default, variable)
   - 1 swimming template (14 week default, variable)
3. `PlanBuilderService` that wires wizard inputs to template selection and parameterisation
4. New API endpoints (preview + create-from-wizard + clone)
5. Frontend wizard component (all 5 steps)
6. Clone plan feature
7. Tests for template generation and validation compliance

### Phase 2: AI-Assisted Generation (Premium)

1. `AIPlanGenerator` class with structured prompting and output parsing
2. Validation loop (generate -> validate -> retry/flag)
3. Toggle in wizard Step 4 to select AI mode
4. Rate limiting and usage tracking (for billing)
5. API key management

### Phase 3: Polish

1. Plan comparison view (diff two plans side by side)
2. Plan sharing (export as link / PDF)
3. Community templates (user-submitted templates)
4. Adaptive re-planning (mid-plan adjustments based on actuals vs plan)

---

## Open Questions

1. ~~**Swimming event taxonomy**~~ **DECIDED**: Support both pool and open water events. The wizard event list for swimming:
   - **Pool**: 400m, 800m, 1500m
   - **Open Water**: 1km, 2.5km, 5km, 10km
   - The user selects pool or open water first, then the distance. This distinction drives template differences (pool plans include more technique/turns work; open water plans include sighting, drafting, navigation skills and potentially wetsuit sessions).
2. ~~**Template sourcing**: Where do the actual training plan structures come from?~~ **DECIDED**: Custom-designed templates built from established, generic sports science principles (periodisation phases, 80/20 intensity distribution, 10-15% weekly volume progression, step-back weeks). No proprietary methodology licensing needed -- these are well-established, freely available training principles.
3. ~~**Profile ownership**: Plan-scoped or user-scoped?~~ **DECIDED**: User-scoped. Profile data (age, weight, experience) lives on `RunnerProfile` and persists across plans, as per existing model. Note: `events_completed` may need to be stored per event type in a JSON map rather than a single integer (e.g. `{"marathon": 3, "half_marathon": 5}`).
4. ~~**Volume units**~~ **DECIDED**: Swimming uses the same workout schema as running -- distance (in metres) + description. No separate sets/reps/rest modelling. Set breakdowns can be written in the description field (e.g. "4x400m @ threshold, 30s rest") but the data model stays consistent across both sports. This keeps the existing `PlanWorkout` table and UI components working for both without forking.
5. ~~**Heart rate / pace zones**: Should the wizard collect these?~~ **DECIDED**: Depends on level.
   - **Beginner**: Zones are auto-calculated from profile data (age, weight) using standard formulas (e.g. age-based max HR, Karvonen for HR zones, VDOT-style pace zones). No user input required -- keeps the wizard simple for beginners.
   - **Intermediate / Advanced**: User is given the choice -- either accept pre-calculated zones or enter their own (from lactate testing, Garmin data, etc.). This respects experienced athletes who already know their zones.
   - In both cases, calculated/entered zones are saved to `RunnerProfile.training_zones_json` / `swim_zones_json` and used by the template engine to prescribe workout intensities.
6. **Default plan length**: 14 weeks is the typical baseline for both running and swimming. The wizard allows the user to adjust this (week count is variable), but 14 weeks is the sensible default for most event types.

---

## Next Steps

Once the above is agreed upon, the first PR should be:
1. Alembic migration for new columns
2. Template engine with one complete template (e.g. marathon intermediate 16-week)
3. Preview endpoint
4. Wizard UI shell (steps navigate, form state accumulates, calls preview)

This gives an end-to-end vertical slice to validate the approach before building out remaining templates and features.
