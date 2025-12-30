# Training Assistant Instructions

When working in this workspace, always refer to the following files to maintain context of the marathon training plan:

1. [plan.json](plan.json): The source of truth for the 14-week training schedule.
2. [context.json](context.json): The source of truth for goals, milestones, and current progress.

### Guidelines:
- Always check the current date relative to the plan in [plan.json](plan.json).
- If the user asks about "today" or "this week", calculate the current week of the plan based on the "weekStarting" dates.
- **Cramp Prevention Focus:** Prioritize advice on fueling (90g carbs/900mg sodium), strength work (calf raises), and pacing (PLR) to solve the 30km cramp issue.
- **Style Rule:** Strictly no emojis in any responses, code, or documentation.
- **Weight Management:** Keep in mind the 97kg -> 90kg target and how it affects mechanical load and fueling needs.
- Maintain the "Training Philosophy" (e.g., Monday Rest, Wednesday Doubles, Thursday Trails) when suggesting adjustments.
- Update [context.json](context.json) when milestones are reached or goals change.
- **Self-Update Protocol:** At the start of each session, review the project structure, `plan.json`, `context.json`, and `roadmap.md`. Proactively suggest updates to `context.json` to ensure the "status" remains accurate.
