# Release Notes

## [v0.0.7] - 2026-01-10

### Added
- **Trail Running**: Explicit support for trail running activities in the plan structure.
- **Dashboard Progress**: Added a "Progress" column to the dashboard table, displaying Target, Current, and Projected status.

### Changed
- **CI/CD Frequency**: Increased Garmin data fetching frequency from daily to **hourly** to provide near real-time updates.
- **Deployment Logic**: Configured the deployment pipeline to trigger automatically upon successful retrieval of "Actuals" from Garmin.

### Fixed
- **Data Accuracy**: Corrected the logic for calculating "Actual" distance totals to ensure better alignment with Garmin data.

## [v0.0.6] - 2026-01-06

### Added
- **Fridge Mode**: High-contrast, A4-optimized physical checklists available via the dashboard "Print Week" button and `generate_fridge_sheets.py`.

### Changed
- **Timezone Alignment**: Migrated all automated logic and Garmin data fetching from GMT/UTC to **AWST (Perth, UTC+8)** to ensure calendar synchronization.

## [Earlier Releases]

### Added
- **Weight Tracking**: Introduced `update_weight.py` and tracking history in `context.json` to monitor the 97kg -> 90kg target.
- **Nightly Sync**: Configured GitHub Actions to automatically fetch Garmin "Actuals" at 00:00 AWST daily.

### Changed
- **Dependency Management**: Fully migrated to `uv` for deterministic builds and faster environment setup.
- **API Modernization**: Replaced deprecated `datetime.utcnow()` with timezone-aware `datetime.now(timezone.utc)`.

### Fixed
- **Dashboard Layout**: Resolved layout squishing on mobile devices.
- **Sync Logic**: Improved Garmin API error handling and retry logic.
