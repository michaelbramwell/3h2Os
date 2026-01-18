from dataclasses import dataclass
from typing import List, Optional
from app.models.domain import Week, Workout

@dataclass
class ValidationIssue:
    severity: str  # "error", "warning"
    message: str
    rule_id: str
    context: Optional[dict] = None

class ValidationEngine:
    def __init__(self, 
                 max_volume_increase_ratio: float = 1.15,  # 15% max increase
                 max_long_run_ratio: float = 0.40,         # Long run shouldn't be >40% of weekly volume
                 max_intensity_ratio: float = 0.25):       # Hard running shouldn't be >25% (example)
        self.max_volume_increase_ratio = max_volume_increase_ratio
        self.max_long_run_ratio = max_long_run_ratio
        self.max_intensity_ratio = max_intensity_ratio

    def validate_progression(self, previous_week: Week, current_week: Week) -> List[ValidationIssue]:
        """
        Validates the progression from one week to the next.
        """
        issues = []
        
        prev_vol = self._calculate_volume(previous_week)
        curr_vol = self._calculate_volume(current_week)
        
        # Rule 1: Weekly Volume Increase
        if prev_vol > 0:
            ratio = curr_vol / prev_vol
            if ratio > self.max_volume_increase_ratio:
                # We allow a grace buffer for very low mileage weeks (e.g. going 10k -> 12k is >10% but fine)
                # But for now, strict %
                issues.append(ValidationIssue(
                    severity="error",
                    message=f"Volume spike detected: {curr_vol/1000:.1f}km is {(ratio-1)*100:.1f}% increase over previous {prev_vol/1000:.1f}km (Max {int((self.max_volume_increase_ratio-1)*100)}%)",
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
        issues.extend(self.validate_structure(current_week))
        
        return issues

    def validate_structure(self, week: Week) -> List[ValidationIssue]:
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
            ratio = longest_run.distance_m / vol
            if ratio > self.max_long_run_ratio:
                 # Warning if total volume is low (e.g. <30k), otherwise Error
                severity = "warning" if vol < 30000 else "error"
                issues.append(ValidationIssue(
                    severity=severity,
                    message=f"Long run ({longest_run.distance_m/1000:.1f}km) is {ratio*100:.0f}% of weekly volume. Recommended max {int(self.max_long_run_ratio*100)}%",
                    rule_id="long_run_ratio",
                    context={"long_run": longest_run.distance_m, "total": vol}
                ))
        
        # Rule 4: Intensity Ratio (Internal)
        # Intensity shouldn't be > X% of total volume (usually 20-30%)
        int_vol = self._calculate_intensity_volume(week)
        int_ratio = int_vol / vol
        if int_ratio > self.max_intensity_ratio: # e.g. 0.25 (25%)
             issues.append(ValidationIssue(
                    severity="warning",
                    message=f"High Intensity ({int_vol/1000:.1f}km) is {int_ratio*100:.0f}% of weekly volume. Recommended max {int(self.max_intensity_ratio*100)}% (80/20 Rule)",
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
                if longest is None or w.distance_m > longest.distance_m:
                    longest = w
        return longest
