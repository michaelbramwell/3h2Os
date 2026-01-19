from dataclasses import dataclass
from typing import List, Optional
from app.models.domain import Week, Workout, ActivityType

@dataclass
class ValidationIssue:
    severity: str  # "error", "warning"
    message: str
    rule_id: str
    context: Optional[dict] = None

class ValidationWarningError(Exception):
    def __init__(self, issues: List[ValidationIssue]):
        self.issues = issues
        self.message = "\n".join([i.message for i in issues])
        super().__init__(self.message)

class ValidationEngine:
    def __init__(self, 
                 max_volume_increase_ratio: float = 1.15,  # 15% max increase
                 max_long_run_ratio: float = 0.40,         # Long run shouldn't be >40% of weekly volume
                 max_intensity_ratio: float = 0.25):       # Hard running shouldn't be >25% (example)
        self.max_volume_increase_ratio = max_volume_increase_ratio
        self.max_long_run_ratio = max_long_run_ratio
        self.max_intensity_ratio = max_intensity_ratio

    def validate_progression(self, previous_week: Week, current_week: Week, focused_workout: Optional[Workout] = None) -> List[ValidationIssue]:
        """
        Validates the progression from one week to the next.
        """
        issues = []
        
        prev_vol = self._calculate_volume(previous_week)
        curr_vol = self._calculate_volume(current_week)
        
        # Rule 1: Weekly Volume Increase
        if prev_vol > 0:
            diff = curr_vol - prev_vol
            # Buffer: If the absolute increase is small (< 5km), ignore percentage rules
            # This prevents flagging 10km -> 14km (40% jump) which is generally safe
            if diff > 5000:
                ratio = curr_vol / prev_vol
                if ratio > self.max_volume_increase_ratio:
                    # We allow a grace buffer for very low mileage weeks (e.g. going 10k -> 12k is >10% but fine)
                    # But for now, strict %
                    issues.append(ValidationIssue(
                        severity="error",
                        message=f"Saving this activity puts the weekly volume at {curr_vol/1000:.1f}km ({(ratio-1)*100:.1f}% increase over previous week). Max recommended increase is {int((self.max_volume_increase_ratio-1)*100)}%.",
                        rule_id="volume_progression",
                        context={"prev": prev_vol, "curr": curr_vol}
                    ))

        # Rule 3: Intensity Progression
        # Check if high-intensity volume increases too sharply
        prev_int_vol = self._calculate_intensity_volume(previous_week)
        curr_int_vol = self._calculate_intensity_volume(current_week)
        
        if prev_int_vol > 0:
            int_ratio = curr_int_vol / prev_int_vol
            # Allow slightly more fluctuation in intensity blocks, but flag big jumps (>25%)
            if int_ratio > 1.25:
                 issues.append(ValidationIssue(
                    severity="warning",
                    message=f"Intensity volume spike: {curr_int_vol/1000:.1f}km is {(int_ratio-1)*100:.1f}% increase over previous {prev_int_vol/1000:.1f}km",
                    rule_id="intensity_progression",
                    context={"prev": prev_int_vol, "curr": curr_int_vol}
                 ))

        # Check internal consistency of the current week too
        issues.extend(self.validate_structure(current_week, focused_workout))
        
        return issues

    def validate_structure(self, week: Week, focused_workout: Optional[Workout] = None) -> List[ValidationIssue]:
        """
        Validates a single week for internal safety/consistency (e.g. Long run ratio).
        """
        issues = []
        vol = self._calculate_volume(week)
        
        if vol == 0:
            return issues

        # Rule 2: Long Run Ratio
        longest_run = self._get_longest_run(week)
        if longest_run:
            # Filter: If we are focusing on a specific workout, and this isn't it, skip this check
            # This ensures we only warn about the long run if the user is actively editing/adding the long run
            if focused_workout and longest_run.name != focused_workout.name:
                pass
            else:
                ratio = longest_run.distance_m / vol
                if ratio > self.max_long_run_ratio:
                    # Warning if total volume is low (e.g. <30k), otherwise Error
                    severity = "warning" if vol < 30000 else "error"
                    issues.append(ValidationIssue(
                        severity=severity,
                        message=f"This activity ('{longest_run.name}') accounts for {ratio*100:.0f}% of the total weekly volume ({int(self.max_long_run_ratio*100)}% recommended max).",
                        rule_id="long_run_ratio",
                        context={"long_run": longest_run.distance_m, "total": vol}
                    ))
        
        # Rule 4: Intensity Ratio (Internal)
        # Intensity shouldn't be > X% of total volume (usually 20-30%)
        
        # Filter: Only warn about intensity balance if the user is touching an intensity workout
        check_intensity = True
        INTENSITY_TYPES = ["interval", "intervals", "tempo", "threshold", "steady", "race", "fartlek", "hill", "hills"]
        
        if focused_workout:
             is_focus_intensity = any(t in focused_workout.type.lower() for t in INTENSITY_TYPES)
             if not is_focus_intensity:
                 check_intensity = False

        if check_intensity:
            int_vol = self._calculate_intensity_volume(week)
            int_ratio = int_vol / vol
            if int_ratio > self.max_intensity_ratio: # e.g. 0.25 (25%)
                 issues.append(ValidationIssue(
                        severity="warning",
                        message=f"This activity puts the weekly High Intensity volume at {int_ratio*100:.0f}% (Recommend ~{int(self.max_intensity_ratio*100)}% / 80/20 Rule).",
                        rule_id="intensity_ratio",
                        context={"intensity": int_vol, "total": vol}
                 ))

        return issues

    def _calculate_volume(self, week: Week) -> float:
        total = 0
        if not week.days:
            return 0
        for day in week.days.values():
            for w in day.workouts:
                if w.type in [ActivityType.CYCLING, ActivityType.SWIMMING]:
                    continue
                total += w.distance_m
        return total
    
    def _calculate_intensity_volume(self, week: Week) -> float:
        # Define types that count towards "Quality/Intensity"
        # Everything else (Easy, Long, Recovery) is base.
        INTENSITY_TYPES = ["interval", "intervals", "tempo", "threshold", "steady", "race", "fartlek", "hill", "hills"]
        total = 0
        if not week.days:
            return 0
        for day in week.days.values():
            for w in day.workouts:
                w_type = w.type.lower()
                # Check for "Mixed" types or if type is just a description
                if any(t in w_type for t in INTENSITY_TYPES):
                    total += w.distance_m
        return total

    def _get_longest_run(self, week: Week) -> Optional[Workout]:
        longest = None
        if not week.days:
            return None
        for day in week.days.values():
            for w in day.workouts:
                if w.type in [ActivityType.CYCLING, ActivityType.SWIMMING]:
                    continue
                if longest is None or w.distance_m > longest.distance_m:
                    longest = w
        return longest
