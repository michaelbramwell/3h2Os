from datetime import date, timedelta

from app.models.domain import EventType
from app.schemas import WizardInput


EVENT_LABELS = {
    EventType.FIVE_K.value: "5K",
    EventType.TEN_K.value: "10K",
    EventType.HALF_MARATHON.value: "Half Marathon",
    EventType.MARATHON.value: "Marathon",
    EventType.ULTRA.value: "Ultra",
    EventType.POOL_400.value: "400m Pool",
    EventType.POOL_800.value: "800m Pool",
    EventType.POOL_1500.value: "1500m Pool",
    EventType.OW_1K.value: "1km Open Water",
    EventType.OW_2_5K.value: "2.5km Open Water",
    EventType.OW_5K.value: "5km Open Water",
    EventType.OW_10K.value: "10km Open Water",
}

MANUAL_EVENT_LABEL = "No Event (Build Weekly)"


def project_snapshot_from_wizard(wizard: WizardInput) -> dict[str, date | str]:
    event_label = EVENT_LABELS.get(
        wizard.sport_event.event_type,
        MANUAL_EVENT_LABEL
        if wizard.sport_event.event_type == "none"
        else wizard.sport_event.event_type,
    )

    goal_label = wizard.goals_focus.primary_goal.replace("_", " ").capitalize()
    if wizard.goals_focus.target_time:
        goal_label = f"Target: {wizard.goals_focus.target_time}"

    event_date = wizard.sport_event.event_date or (
        date.today() + timedelta(weeks=wizard.plan_config.total_weeks)
    )

    return {
        "name": wizard.sport_event.event_name or f"{event_label} Training",
        "goal": goal_label,
        "event": event_label,
        "event_date": event_date,
    }
