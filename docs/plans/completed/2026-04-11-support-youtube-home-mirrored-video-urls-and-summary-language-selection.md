---
# Support youtube.home mirrored video URLs and summary language selection

## Overview
Make the site work when a user opens a YouTube video URL and replaces `.com` with `.home`, so the app can infer the original video and auto-generate a summary without manual pasting. Add a language dropdown limited to English and Russian that controls the summary output language independently from the transcript language.

## Context
- Files involved: `summarizer/web.py`, `summarizer/templates/index.html`, `summarizer/app.py`, `summarizer/gemini.py`, `summarizer/file_handler.py`, `summarizer/youtube.py`, `tests/test_youtube.py`, `tests/test_gemini.py`, `README.md`
- New test files likely needed: `tests/test_web.py`, `tests/test_file_handler.py`
- Related patterns: the current UI auto-submits when `?video_url=` is present; the Flask app currently only serves `/`; `YouTubeURLValidator` owns URL parsing; summary cache filenames currently include only `video_id` and transcript language
- Dependencies: no new runtime dependencies should be needed; existing dev tooling already includes `pytest`, `black`, and `isort`
- Key constraint: summary language and transcript language must be treated as separate values end-to-end, otherwise cached summaries can be returned in the wrong language after the dropdown changes

## Development Approach
- Testing approach: Regular (route/backend changes first, then template wiring)
- Complete each task fully before moving to the next
- Preserve the existing `?video_url=` entrypoint so the Firefox extension and local/manual flows keep working
- Keep the implementation simple: normalize mirrored `youtube.home` requests into canonical `youtube.com` video URLs instead of building a YouTube-like router
- Use English as the initial dropdown default unless product requirements change later
- CRITICAL: every task MUST include new or updated tests
- CRITICAL: all tests must pass before starting the next task

## Implementation Steps

### Task 1: Support mirrored youtube.home video URLs

**Files:**
- Modify: `summarizer/web.py`
- Modify: `summarizer/youtube.py`
- Modify: `tests/test_youtube.py`
- Create: `tests/test_web.py`

- [x] add a catch-all GET route so paths like `/watch?...` and `/shorts/...` render the summarizer page instead of returning 404
- [x] normalize incoming `youtube.home` request path and query into a canonical `https://youtube.com/...` video URL while still honoring explicit `?video_url=` overrides
- [x] extend URL parsing to accept the mirrored direct-video formats the new flow depends on, especially standard watch URLs and shorts URLs
- [x] write tests for mirrored request handling, canonical URL reconstruction, and invalid non-video paths
- [x] run `python -m pytest tests/test_youtube.py tests/test_web.py` - passed via `./venv/bin/python -m pytest tests/test_youtube.py tests/test_web.py` because `python` is unavailable in this environment

### Task 2: Add summary-language selection to the API and summarizer

**Files:**
- Modify: `summarizer/web.py`
- Modify: `summarizer/app.py`
- Modify: `summarizer/gemini.py`
- Modify: `tests/test_gemini.py`
- Modify: `tests/test_web.py`

- [x] accept a new `summary_language` field in `/api/summarize`
- [x] validate `summary_language` server-side and allow only `en` and `ru`
- [x] pass the requested summary language into Gemini prompt generation instead of always using the transcript language
- [x] return separate response fields for transcript language and summary language so the UI is not forced to overload the current ambiguous `language` field
- [x] write tests for API validation, prompt generation, and the response contract
- [x] run `python -m pytest tests/test_gemini.py tests/test_web.py` - passed via `./venv/bin/python -m pytest tests/test_gemini.py tests/test_web.py` because this environment does not provide a `python` alias

### Task 3: Make summary caching safe for language switching

**Files:**
- Modify: `summarizer/app.py`
- Modify: `summarizer/file_handler.py`
- Create: `tests/test_file_handler.py`

- [x] change summary cache lookup and save behavior so cache keys include both transcript language and requested summary language
- [x] record transcript language and summary language separately in saved summary metadata and filenames
- [x] keep transcript caching unchanged so transcript reuse still works independently of summary output language
- [x] write tests that prove switching the dropdown from English to Russian does not return a stale cached summary in the wrong language
- [x] run `python -m pytest tests/test_file_handler.py tests/test_web.py` - passed via `./venv/bin/python -m pytest tests/test_file_handler.py tests/test_web.py` because this environment does not provide a `python` alias

### Task 4: Add the English/Russian dropdown and auto-submit UI flow

**Files:**
- Modify: `summarizer/templates/index.html`
- Modify: `summarizer/web.py`
- Modify: `tests/test_web.py`

- [x] add a dropdown to the form with only two options: English and Russian
- [x] include the selected summary language in the existing POST payload
- [x] auto-populate and auto-submit when the page is opened through the mirrored `youtube.home` route, while preserving the current `?video_url=` auto-submit behavior
- [x] update result labels so transcript language and summary language are shown explicitly and no longer conflated in a single badge
- [x] write template/render tests that assert the dropdown exists and the page still renders correctly for both root and mirrored video routes
- [x] run `python -m pytest tests/test_web.py` - passed via `./venv/bin/python -m pytest tests/test_web.py` because this environment does not provide a `python` alias

### Task 5: Verify acceptance criteria

**Files:**
- Modify: none

- [x] run `python -m pytest tests/` - passed via `./venv/bin/python -m pytest tests/` because this environment does not provide a `python` alias
- [x] run `black --check .` - passed via `./venv/bin/black --check .`
- [x] run `isort --check-only .` - passed via `./venv/bin/isort --check-only .`
- [x] verify test coverage meets 80%+ using the project coverage command or CI job before merge (skipped - not automatable in this environment because `pytest-cov`/`coverage` is not installed and `./venv/bin/python -m pytest --cov=summarizer tests/` is rejected)

### Task 6: Update documentation

**Files:**
- Modify: `README.md`

- [x] document the `youtube.home` mirrored-URL flow with an example URL
- [x] document that the summary language dropdown supports only English and Russian
- [x] document that the legacy `?video_url=` flow still works for the Firefox extension and local/manual use
- [x] move this plan to `docs/plans/completed/`
---
