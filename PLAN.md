# talk-tracker — Build Plan

Status: v1.3 (2026-10-07) — scope decisions resolved (see §0); M0 complete; M1 survey done from search, awaiting live probe (see §12). Owner: Fermilab DM & DE group (`fnal-cpc/talk-tracker`).

## 0. Resolved decisions (2026-10-06)

1. **Scope:** the 10 pilot institutions only (§6). Expansion to ~50 later.
2. **No conference talks** in v1. Indico is used only where a *seminar/colloquium series* is hosted on Indico (e.g. lab seminar series), not for conference agendas.
3. **No LLM API key.** The `llm` adapter is dropped from v1; bespoke pages use the `html` (CSS selectors) or `browser` (Playwright) adapters, or are marked `unsupported`.
4. **Public repository** (`fnal-cpc/talk-tracker`). The event archive therefore contains only publicly posted event information; no login-protected pages are scraped.
5. **Affiliated students and postdocs are included** in the roster and in reports, labeled with their role.
6. **No roster in the repository.** The package is people-agnostic: the roster is supplied at run time from the user's own context (the "Group Members" project doc or the header of the Previous Reports Google Doc). The repo contains no names, ORCIDs, or name-collision lists of real people. Tests use fictional names.

## 1. Goal

Find talks given by members of the Fermilab Dark Matter & Dark Energy group (and affiliated postdocs/students) at physics and astronomy colloquia and seminars across research institutions (10 in the pilot; ~50 eventually), and produce a monthly list in the format used by the group's monthly reports:

```
* Invited Talks:
  * <Speaker>, <Colloquium|Seminar|Invited talk>, <Series>, <Institution> — <date>, <URL>
```

Success is measured by **recall** against talks already known from previous monthly reports, and **precision** of roster matches (few false positives from name collisions).

### Non-goals (for now)
- Automatic monthly report generation (literature search, news) — handled separately by the Claude project workflow.
- Unattended scheduling — added in a later milestone (GitHub Actions), not required for v1.
- Capturing every talk in the world; we target series where the group is likely to be invited.

## 2. Key design decisions

| Decision | Choice | Reason |
|---|---|---|
| Language | Python ≥ 3.11 | Ecosystem for iCal/HTML parsing; group familiarity |
| Unit of configuration | **Seminar series**, not institution | Institutions host several relevant series on different platforms |
| Scraping strategy | **One adapter per platform**, configured per series | University calendars run on a handful of platforms with structured feeds; avoids one scraper per site |
| Storage | Append-only JSON Lines in the repo (`data/events/`) | Diffable, versioned in git, no database server |
| Accumulation | Scrape repeatedly (weekly once automated) and keep everything ever seen | Many department pages drop past events |
| Matching | Full-name match against roster variants; weak matches flagged, never silently accepted | Same-name collisions were frequent in the literature search |
| People data | Roster and known-talk lists are run-time inputs, never committed | Keeps the public repo people-agnostic; single source of truth stays in the group's own docs |
| "Invited" | Derived from series type (colloquium/seminar ⇒ invited) | Satisfies the report's requirement to state why a talk is invited |
| LLM extraction | Not in v1 (no API key) | Revisit if a key becomes available; would reduce per-site parser effort for bespoke HTML |

## 3. Repository layout

```
talk-tracker/
├── PLAN.md
├── README.md
├── pyproject.toml
├── registry/
│   ├── schema.json                # JSON Schema for institution files
│   └── institutions/
│       ├── uchicago.yaml
│       ├── fnal.yaml
│       └── ...
├── src/talk_tracker/
│   ├── __init__.py
│   ├── cli.py                     # entry point: `talk-tracker ...`
│   ├── models.py                  # Series, RawEvent, Event, Match (pydantic)
│   ├── registry.py                # load/validate registry; list domains
│   ├── fetch.py                   # HTTP client: rate limit, robots.txt, caching, retries
│   ├── adapters/
│   │   ├── base.py                # Adapter protocol
│   │   ├── ical.py                # .ics feeds (Google Calendar, Trumba, Drupal, etc.)
│   │   ├── localist.py            # Localist JSON API
│   │   ├── tribe.py               # WordPress "The Events Calendar" REST API
│   │   ├── indico.py              # Indico HTTP export API (seminar series only)
│   │   ├── rss.py                 # RSS/Atom event feeds
│   │   ├── html.py                # CSS-selector-configured HTML scraping
│   │   └── browser.py             # Playwright for JS-rendered pages (optional)
│   ├── parse.py                   # split "Speaker (Affil): Title" strings, date handling
│   ├── archive.py                 # upsert into data/events/*.jsonl, dedupe
│   ├── roster.py                  # parse a roster supplied at run time (see §4.2)
│   ├── match.py                   # roster matching with confidence levels
│   ├── report.py                  # monthly report rendering (markdown)
│   └── health.py                  # per-series status, staleness detection
├── data/
│   ├── events/YYYY-MM.jsonl       # archive, partitioned by event month
│   └── runs/YYYY-MM-DDTHHMM.json  # run logs: per-series status/counts/errors
├── tests/
│   ├── fixtures/<series_id>/...   # saved .ics/.json/.html responses
│   ├── test_adapters.py
│   ├── test_parse.py
│   ├── test_match.py
│   └── test_registry.py
└── .github/workflows/
    ├── ci.yml                     # lint + tests on PR
    └── scrape.yml                 # (milestone 6) weekly scrape + commit
```

## 4. Data model

### 4.1 Registry (one YAML file per institution)

```yaml
id: uchicago
name: University of Chicago
country: US
timezone: America/Chicago
series:
  - id: uchicago-physics-colloquium
    name: Physics Colloquium
    type: colloquium            # colloquium | seminar | lecture | other  (conference: not in v1)
    invited: true               # default derived from type; override if needed
    url: https://...            # human-facing page (evidence link)
    adapter: localist           # ical | localist | tribe | indico | rss | html | browser
    params:                     # adapter-specific
      base_url: https://...
      group: physics
      keyword: colloquium
    domains: [events.uchicago.edu]
    keeps_past_events: unknown  # true | false | unknown (determined during survey)
    active: true
    verified: false             # true once the feed/adapter is confirmed live (talk-tracker probe)
    notes: ""
```

`talk-tracker domains` prints the union of all `domains` (for the network allowlist and for the fetcher's own allowlist).

### 4.2 Roster (supplied at run time, never committed)

The roster is an **input**, passed with `--roster PATH` (or `-` for stdin). Scraping does not need it: the archive stores *all* events from registered series, and matching happens only at report time. `.gitignore` excludes `roster*`, `*.roster.*` and `members*` files to prevent accidental commits.

Accepted formats:

1. **Group-Members text** (the format of the project doc / Google Doc header), parsed directly so the doc can be exported and passed as-is:
   ```
   Current Group Members:
   * Firstname Lastname (0000-0000-0000-0000)
   Joint Appointments:
   * Firstname Lastname (Institution; 0000-0000-0000-0000)
   Former Members: ...
   Affiliated Postdocs: ...
   Affiliated Students: ...
   ```
   Section headings map to roles (`member`, `joint`, `former`, `postdoc`, `student`). Name variants are generated automatically (full name, first initial + surname, with/without middle initials, hyphen/space and accent variants).
2. **YAML/JSON** for richer input when needed:
   ```yaml
   - name: Firstname Lastname
     role: student
     orcid: 0000-0000-0000-0000      # optional
     variants: ["F. Lastname"]       # optional, added to generated variants
     associated_with: ["Other Member"]  # optional, report annotation only
     not: ["Firstname2 Lastname"]    # optional, known different people (collisions)
   ```

Typical use from the Claude project: export the "Group Members" doc to a temporary file in the session and pass it with `--roster`; the file is discarded with the session.

### 4.3 Event (archive record)

| Field | Notes |
|---|---|
| `event_id` | sha1(series_id + start date + normalized title) — stable across scrapes |
| `series_id`, `institution_id` | from registry |
| `start` | timezone-aware ISO 8601 |
| `speaker_raw`, `speaker_name`, `speaker_affiliation` | raw string kept for audit; parsed fields may be null |
| `title`, `abstract` | abstract truncated to e.g. 2000 chars |
| `url` | event page if available, else series page |
| `adapter` | which adapter produced it |
| `first_seen`, `last_seen` | scrape timestamps; `last_seen` shows whether the event later disappeared |
| `content_hash` | detect edits (e.g. speaker changes, cancellations) |
| `cancelled` | if the source marks it |

## 5. Components

### 5.1 Fetcher (`fetch.py`)
- `httpx` client with per-domain rate limit (default 1 request / 2 s), timeouts, 3 retries with backoff.
- Respects `robots.txt`; identifies itself with a user agent that names the project and repo URL.
- Refuses domains not listed in the registry (its own allowlist).
- Optional on-disk cache for development (`--cache`), which also lets tests run on saved responses.

### 5.2 Adapters
Each adapter implements `fetch(series, start, end) -> list[RawEvent]` and raises a typed error on failure (recorded in the run log; never silently returns nothing).

| Adapter | Source | Notes |
|---|---|---|
| `ical` | `.ics` URL | `icalendar` + `recurring-ical-events`; covers Google Calendar, Trumba, many Drupal sites |
| `localist` | `/api/2/events?start=&end=&group_id=&keyword=` | JSON; common at US universities |
| `tribe` | `/wp-json/tribe/events/v1/events?start_date=&end_date=` | WordPress "The Events Calendar" |
| `indico` | `/export/categ/<id>.json?from=&to=` | Seminar series hosted on Indico only; skip categories needing auth |
| `rss` | RSS/Atom | Fallback for feeds without dates in structured form |
| `html` | CSS selectors in `params` | For static pages; selectors for item, date, speaker, title, link |
| `browser` | Playwright + `html` selectors | JS-rendered pages; Chromium already available |
| `planitpurple` | `/xmlfeed?cal=<id>&start=mm-dd-yyyy&end=mm-dd-yyyy` | Northwestern PlanIt Purple (added in M1); `archive=1` reaches 4 years back |

### 5.3 Parsing (`parse.py`)
- Many feeds put speaker and affiliation in the title (e.g. `"Colloquium: Jane Doe (MIT) – Dark Matter..."`). Ordered list of regex patterns plus a per-series override pattern in `params.speaker_pattern`.
- Date normalization to the series timezone; handle all-day events and missing times.

### 5.4 Archive (`archive.py`)
- Upsert by `event_id`; update `last_seen`, keep `first_seen`; record content changes.
- Partition files by event month; keep files sorted for clean diffs.

### 5.5 Matching (`match.py`)
- Normalize: Unicode NFKD, strip accents, lowercase, unify hyphens/spaces.
- Search `speaker_name`, then `speaker_raw`, then `title`/`abstract` (speaker often only in text).
- Confidence:
  - **high**: full-name variant match in speaker field.
  - **medium**: full-name match in title/abstract, or initial + surname in speaker field with a plausible affiliation (Fermilab, UChicago, Northwestern, KICP, etc.).
  - **low**: surname-only or initial + surname with no affiliation; listed only in a "needs review" section.
- Known collisions supplied in the roster input (`not:`) force downgrade to low unless the affiliation matches.

### 5.6 Report (`report.py`)
`talk-tracker report --month 2026-09` produces markdown:
```
* Invited Talks:
  * Jane Example, Colloquium, Physics Colloquium, University X — 2026-09-12 [high] <url>
  * Sam Sample (student), Seminar, Astro Seminar, University Y — 2026-09-20 [high] <url>
* Needs review:
  * ...
```
plus a coverage footer: number of series checked, number failing, number with no events in the month.

### 5.7 Health (`health.py`)
`talk-tracker check` reports, per series: last successful fetch, event count over last 90 days, failures. Flags series with zero events for 60+ days during term time (likely moved feeds).

### 5.8 CLI
```
talk-tracker validate [--roster PATH]      # schema-check registry (and a roster, if given)
talk-tracker domains                       # print allowlist domains
talk-tracker list                          # registry as a markdown table
talk-tracker probe [--series ID] [--json PATH]   # survey: detect platform/feeds of series pages
talk-tracker scrape [--series ID] [--from DATE --to DATE] [--cache]
talk-tracker report --month YYYY-MM --roster PATH [--min-confidence medium]
talk-tracker check                         # feed health
talk-tracker backfill --from DATE          # one-off: pull archives where available
talk-tracker evaluate --roster PATH --known PATH   # recall/precision vs known talks
```

## 6. Pilot institution set (10)

Chosen for likelihood that group members are invited; to be revised.

1. University of Chicago (Physics, Astronomy & Astrophysics, KICP)
2. Fermilab (Colloquium, Wine & Cheese, Astrophysics seminars)
3. Northwestern (Physics & Astronomy, CIERA)
4. Stanford / SLAC / KIPAC
5. UC Berkeley / LBNL (Physics, Astronomy, BCCP seminars)
6. Caltech (Physics, Astronomy, TAPIR)
7. Princeton / IAS
8. Harvard / CfA
9. MIT (Physics, MKI)
10. University of Michigan (Physics, Astronomy, LCTP)

For each: identify 2–4 series, the platform, feed URL, whether past events are retained.

**Known gap:** talks recorded in previous reports include non-US venues (e.g. LPSC Grenoble, Kavli/KICC Cambridge). The full ~50 list must include European and South American hosts (CERN, Cambridge, Oxford, Durham, MPIA/MPA/MPP, IAP/LPSC, ICTP-SAIFR, Buenos Aires/Bariloche, etc.) and major conferences via Indico.

## 7. Milestones

| # | Milestone | Deliverable | Exit criterion |
|---|---|---|---|
| M0 | Skeleton | package, CLI stub, models, CI, schema, run-time roster parser | `pytest` and `talk-tracker validate` pass in CI |
| M1 | Pilot survey | 10 institution YAMLs; survey table (series, platform, feed, past-event retention) | Every pilot series has an adapter assignment or is marked `unsupported` with a reason |
| M2 | Adapters | `ical`, `localist`, `tribe`, `indico`, `html` with fixtures and tests | All pilot series with feeds fetch successfully against fixtures; live where the domain is reachable |
| M3 | Archive + matching | `archive.py`, `roster.py`, `match.py`, `parse.py` | Re-running scrape is idempotent; matcher passes collision tests (fictional names) |
| M4 | Report + validation | `report`, `backfill`, `check` | Backfill 12 months on pilot; compare against talks in previous reports; record recall and precision |
| M5 | Scale to ~50 (later) | remaining registry entries; `browser` adapter if needed | ≥ 80 % of registered series fetch successfully; documented list of unsupported series |
| M6 | Automation | `scrape.yml` weekly GitHub Action committing `data/`; failure notifications | Two consecutive unattended weeks without manual intervention |

## 8. Testing strategy
- **Fixtures**: every series gets saved responses in `tests/fixtures/` (captured once live or via manual download). Adapters are tested offline.
- **Parser golden tests**: title strings → expected (speaker, affiliation, title).
- **Matcher tests**: fictional roster in `tests/fixtures/`; positive cases (variants, accents, hyphens, initials) and negative cases (same surname, same initial, `not:` collisions).
- **Roster parser tests**: fictional Group-Members-format text → expected entries and roles.
- **Registry validation**: JSON Schema; domains present; no duplicate IDs.
- **Recall evaluation (M4)**: `talk-tracker evaluate --roster PATH --known PATH` compares the archive with a list of known talks supplied at run time (derived from previous monthly reports; not committed), restricted to venues in the registry.

## 9. Operations
- **Development here (Claude workspace):** live fetching only for domains on the account's network allowlist; otherwise fixtures. Code is delivered as a git bundle and pushed to `fnal-cpc/talk-tracker` by a human.
- **Development locally / Actions:** no allowlist; full live runs.
- **Secrets:** none required (no LLM adapter; no authenticated Indico).
- **Etiquette:** low request rates, robots.txt respected, weekly cadence; no scraping of login-protected pages.

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Pages drop past events | Weekly accumulation; `keeps_past_events` recorded; backfill where archives exist |
| Speaker not in a structured field | Title/abstract parsing; per-series patterns; full-text roster search |
| Feeds move or break each term | `check` command; failures logged per run; health section in report |
| Name collisions | Full-name matching, affiliation check, known-collision list, review section |
| JS-only calendars | Playwright adapter; mark `unsupported` if cost too high |
| Terms of use / robots.txt | Respect robots.txt; skip disallowed series; low rate |
| Conference talks not captured | Out of scope for v1; continue to find them via web search in the monthly workflow |
| Coverage bias of institution list | Revisit list using venues from previous reports and recall misses |

## 11. Open questions
1. Affiliation of postdocs/students with members (`associated_with`) is optional roster input; if wanted, it should be added to the Group Members doc rather than to this repo.
2. Pilot recall can only be measured on previously reported talks held at pilot venues; talks at other venues or conferences (e.g. the September 2026 talks at LPSC Grenoble and the Kavli Symposium, Cambridge) fall outside the pilot. The size of the usable validation sample is not yet known.

## 12. Progress log

### M0 — skeleton (2026-10-07)
Delivered: package (`src/talk_tracker`), `pyproject.toml` (deps: pydantic, PyYAML, jsonschema; CLI on stdlib `argparse`), models, `registry/schema.json` + three-layer registry validation (JSON Schema → pydantic → cross-file rules), run-time roster parser (Group-Members text, YAML, JSON), adapter protocol, CLI (`validate`, `domains` working; other commands stubbed with exit status 2), CI (ruff + pytest + `talk-tracker validate` on Python 3.11–3.13), 64 tests on fictional data.

Decisions and deviations made during M0:
- `adapter: unsupported` is a schema value (M1 needs it); it requires `notes`.
- Series ids must be prefixed with the institution id; institution files must be named `<id>.yaml`.
- Every http(s) URL in `params` must be on a host in the series' `domains` (keeps the fetcher allowlist complete). The human-facing `url` is exempt.
- `invited` defaults to true for `lecture` as well as `colloquium`/`seminar`.
- `.gitignore`: `roster*` would also have hidden `roster.py`, so `!roster.py` is added; `known_talks*` and `*.known.*` are also ignored. Test fixtures for people live in `tests/fixtures/people/`.
- `tests/test_no_people_data.py` fails on any checksum-valid ORCID iD outside a fictional allowlist, and checks the ignore rules.
- Roster text parser: headings may carry a parenthetical note (e.g. "Known Name Conflicts (…):"); the `Known Name Conflicts` section is parsed into each person's `not:` list; a conflict entry naming an unknown person is an error; ORCID checksums are verified.
- Name variants: full name, name without initials, first spelled given name + surname, "Surname, Given", and initial forms (stored separately as weak evidence). Surname = last token, so unhyphenated compound surnames need explicit `variants`.
- No license chosen yet (`pyproject.toml` has none) — to be decided by the owners before the repo is public.

Checked against the current Group Members doc in a session (not committed): 24 entries parsed (6 member, 4 joint, 5 postdoc, 7 student, 2 former), all ORCID checksums valid, conflict names extracted for 7 people.

### M1 — pilot survey (2026-10-07; live confirmation pending)
Delivered: 10 institution files (32 series) in `registry/institutions/`, `docs/survey.md` (method, summary, gaps, generated table), `talk-tracker probe` (platform/feed detection on series pages, optional feed checks, markdown + JSON output), `talk-tracker list`.

How the survey was done: the Claude workspace cannot reach university or lab sites from its shell, and its page fetcher returns extracted text without `<head>`/feed links (and sometimes stale copies). Assignments were therefore made from web search and page text. All series are `verified: false`. The exit criterion ("every pilot series has an adapter assignment or is marked unsupported") is met provisionally. M1 is complete once `talk-tracker probe` has been run from a normal network and its results applied.

Decisions and deviations made during M1:
- New registry field `verified` (default false).
- New adapter `planitpurple` (Northwestern), to be implemented in M2 alongside the others.
- A registry series may be a listing page that mixes several named series (e.g. UChicago A&A/KICP colloquia, IAS astrophysics calendar); the per-event series label will need to be parsed in M2.
- KIPAC tea talks and ITC luncheons are registered as `type: other` (not invited by default) so that they show up only for review.
- `html` with `params.list_url` is used as the placeholder where no feed was identified: 19 of 32 series. The probe is expected to move some of them to structured adapters.
- Not registered (pages not found by search): Princeton Physics Colloquium, MIT Physics Colloquium. See `docs/survey.md`.

