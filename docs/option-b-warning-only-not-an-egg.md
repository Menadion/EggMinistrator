# Proposal: Option B — Warning-Only `not_an_egg` Handling

**Status:** Proposed — requires approval from M before implementation.

## Purpose

Use `not_an_egg` as a failed-scan response instead of a database record. This is intended for
cases where the candling camera sees a hand, an empty station, or an incorrectly positioned egg.

## Proposed Flow

```text
Inspector starts a scan
    → ESP32 captures one candling image and sends it to the server
    → AI classifier returns good, defective, or not_an_egg

good / defective
    → save the inspection, weight, size grade, and AI result to the database
    → show the result to the inspector

not_an_egg
    → do not create an egg_inspections row
    → do not create an ai_assessments row
    → do not store the photo, weight, or a database event
    → show a warning on the station screen:
      "No egg detected. Place one egg correctly and scan again."
    → allow the inspector to retry
```

## Dashboard Behavior

- Dashboard, History, Reports, and Analytics show only valid egg inspections.
- `not_an_egg` does not affect totals, egg-size distribution, average weight, or defect rate.
- No Device Diagnostics page is required for this option.

## Why Consider This Option

- Gives the inspector an immediate, simple instruction on the station screen.
- Keeps the database focused on valid egg inspections.
- Avoids filling reports and history with hand/empty-camera scans.
- Matches the current situation while hardware is not yet available.

## Trade-Off

The team will not be able to count or investigate repeated failed scans later. For example, it will
not reveal whether poor camera positioning, lighting, or station timing is causing many retries.

## Contract Impact

The current `CONTRACT.md` says classifier results land in `ai_assessments`, including
`not_an_egg`. If this proposal is approved, M must update that contract before the backend and
firmware implement this behavior.

The existing database ENUM values can remain unchanged for future compatibility; Option B simply
does not insert a row when the classifier returns `not_an_egg`.

## Questions for Team Approval

1. Should the station screen also use a red LED or short buzzer for the warning?
2. What exact station-screen message should the inspector see?
3. Should the backend return a retry response to the ESP32, and what should its JSON format be?
4. Should connection and camera failures use separate warning messages from `not_an_egg`?

## Acceptance Criteria

1. A valid `good` or `defective` result creates normal database records.
2. A `not_an_egg` result shows the station warning and creates no database records.
3. The inspector can immediately retry the scan.
4. Dashboard totals and reports remain unchanged after a `not_an_egg` result.
