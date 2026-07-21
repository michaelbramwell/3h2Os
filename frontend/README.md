# 3h2Os Frontend

The frontend for the 3h2Os training plan platform, built with React, Vite, and TanStack.

## Tech Stack
- **Framework:** React 19 + Vite
- **Routing:** TanStack Router (File-based routing)
- **State Management:** TanStack Query
- **Styling:** Tailwind CSS
- **Authentication:** OIDC Client (Keycloak) via `react-oidc-context`
- **Language:** TypeScript

## Architecture

```
src/
  main.tsx                  # App entry point
  routes/
    __root.tsx              # Root layout (auth provider, sidebar)
    index.tsx               # Dashboard route (plan view)
    plans.build.tsx         # Plan builder wizard route
  components/
    Sidebar.tsx             # Navigation sidebar with plan switcher
    PlanSwitcher.tsx        # Plan selector with create/delete/clone actions
    WeekCard.tsx            # Week display with status badges
    DayCard.tsx             # Day display within a week
    WorkoutCard.tsx         # Individual workout display
    WeekStats.tsx           # Weekly volume/distance statistics
    ActualCard.tsx          # Completed activity display
    ActivityModal.tsx       # Activity detail modal
    RecentActivities.tsx    # Recent activities list
    EditWorkoutDialog.tsx   # Workout edit form
    EditWeekDialog.tsx      # Week edit form
    CreatePlanDialog.tsx    # Simple plan creation dialog
    ClonePlanDialog.tsx     # Plan clone with date offset
    ContextSection.tsx      # User context display
    FridgeWeek.tsx          # Print-friendly weekly view
    ui/
      ConfirmDialog.tsx     # Reusable confirmation dialog
    wizard/
      PlanWizard.tsx        # Main wizard container (step state machine)
      StepSportEvent.tsx    # Step 1: Sport type and event selection
      StepAthleteProfile.tsx # Step 2: Experience, age, zones
      StepGoalsFocus.tsx    # Step 3: Goals, pain points, availability
      StepPlanConfig.tsx    # Step 4: Plan length, peak volume
      StepReview.tsx        # Step 5: Preview and confirm
      WizardProgress.tsx    # Step indicator bar
      index.ts              # Barrel exports
  hooks/
    useWizard.ts            # Wizard step navigation and form state
    useWorkoutForm.ts       # Workout form state management
  lib/
    api.ts                  # API client (fetch wrapper)
    auth.ts                 # Auth configuration
    dateTime.ts             # Central date/time helpers (formatInstant, formatCalendarDate)
    calculations.ts         # Client-side calculations
    formatters.ts           # Display formatting utilities
  types/
    schema.ts               # TypeScript types matching backend schemas
    wizard.ts               # Wizard-specific types
  providers/
    AuthProvider.tsx         # OIDC auth context provider
```

## Getting Started

1. **Install Dependencies:**
   ```bash
   npm install
   ```

2. **Run Development Server:**
   ```bash
   npm run dev
   ```
   Access the app at `http://localhost:5173`.

   The app requires a running Keycloak instance for authentication. If using Docker (`docker compose up`), this is handled automatically.

3. **Build for Production:**
   ```bash
   npm run build
   ```
   Static assets are output to `dist/`.

4. **Run Tests:**
   ```bash
   npm test
   ```
