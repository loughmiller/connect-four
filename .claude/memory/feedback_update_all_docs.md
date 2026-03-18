---
name: Update all documentation when changing the API
description: When modifying API behavior (new fields, endpoints, parameters), also update the README and src/api_spec.py — not just code and tests
type: feedback
---

When changing the API (adding fields, endpoints, or parameters), always update all documentation surfaces — not just the implementation and tests.

**Why:** Missed updating both the README and the OpenAPI spec (`src/api_spec.py`) when adding player names. Had to make follow-up fixes for both.

**How to apply:** Before considering an API change complete, check and update:
1. `src/api_spec.py` — OpenAPI spec (schemas, request/response bodies, parameters)
2. `README.md` — API usage examples and endpoint descriptions
3. Any other docs that reference the API
