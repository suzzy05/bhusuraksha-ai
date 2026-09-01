# India boundary support

Phase 7 prepares the *architecture* for using a real India administrative
boundary (state/district polygons) — it does not ship one, and never
downloads one automatically.

Configure a real boundary file (e.g. a GeoJSON of Indian state boundaries
from an official source) via:

```bash
BHUSURAKSHA_INDIA_BOUNDARY_PATH=/path/to/india_states.geojson
```

If unset, or the configured file doesn't exist, the application continues
to work normally — anything that would use the boundary (e.g. a spatial
state lookup for a coordinate) reports:

> India boundary dataset not configured.

instead of guessing or fabricating a boundary. See [`boundary.py`](boundary.py)
for the status-check API (`get_boundary_status()`).

**Not yet implemented:** parsing the boundary geometry itself and using it
for spatial lookups (e.g. "which state is this coordinate in?"). This file
documents the configuration surface and the honest fallback behavior;
geometry parsing is a future extension point, not something to fabricate
here.
