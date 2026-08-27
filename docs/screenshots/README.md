# Portfolio Screenshots

Canonical presentation set for the AI Trip Planner assignment and portfolio. Images are captured from the real application with live or sandbox providers—no mock UI chrome.

Recommended desktop viewport: **1440×900** (1280×800 acceptable for empty planner).

**Do not commit** `apps/web/test-results/` — Playwright artifacts are not portfolio assets.

## Canonical files

| File | Demonstrates | Recommended state | Must not appear |
|------|----------------|-------------------|-----------------|
| `01-landing.png` | Marketing entry, product positioning, CTA | Signed-out or signed-in landing at `/` | API keys, `.env`, debug overlays |
| `02-planner-empty.png` | Pre-trip composer | `/planner` empty state with example prompt visible | Completed itinerary, trace drawer |
| `03-completed-trip.png` | Full trip workspace | Dubai 5-day plan complete: header, essentials, budget, day 1 itinerary | Browser devtools, secrets, error banners |
| `04-agent-trace.png` | SSE execution transparency | Trace drawer open on completed or in-flight run | Raw stack traces, JWT tokens |
| `05-trip-modification.png` | Selective refinement | After “Make day 2 more relaxed” with summary visible | Operation metadata wall, fake prices |
| `06-logistics-details.png` | Logistics popovers | Composite: flight + stay + ground detail panels | Invented carrier names, booking CTAs |

## Capture notes

### `01-landing.png`

- Route: `/`
- Show hero headline and primary CTA
- Clerk sign-in in header is fine; hide personal email if publishing publicly

### `02-planner-empty.png`

- Route: `/planner`
- Heading: “Describe your trip.”
- Example Dubai prompt in composer
- Trace drawer closed

### `03-completed-trip.png`

- Route: `/planner/{run_id}` after canonical Dubai prompt completes
- Visible: destination, travelers, route, budget total, trip essentials, day navigator, at least one activity row, composer dock
- Map may be collapsed on mobile captures

### `04-agent-trace.png`

- Open execution trace from completed run
- Show parallel tool successes and provenance chips
- Prefer completed run with all green/success states for portfolio clarity

### `05-trip-modification.png`

- Submit modification prompt; capture summary + updated day
- “Day 02 updated” (or equivalent) and change facts list

### `06-logistics-details.png`

- Composite of three popover captures (`logistics1.png`, `logistics2.png`, `logistics3.png` source files)
- Labels: Flight details · Stay details · Ground details
- Regenerate composite after UI changes:

```bash
uv run --with pillow python scripts/composite_logistics_screenshot.py
```

(if script present) or use the one-off conversion used during doc pass.

## Source captures (optional)

These files are inputs for the logistics composite—not required in README gallery:

- `logistics1.png` — flight popover
- `logistics2.png` — stay popover
- `logistics3.png` — ground travel popover

JPEG originals from early capture passes may be deleted after PNG normalization.

## QA checklist before committing images

- [ ] No browser chrome (unless intentionally cropped)
- [ ] No terminal with secrets visible
- [ ] No hydration error overlay
- [ ] No placeholder “lorem” content
- [ ] Provenance badges match actual provider modes (live / sandbox / reference / estimated)
- [ ] Layout not broken at capture resolution
- [ ] File names match canonical list above
