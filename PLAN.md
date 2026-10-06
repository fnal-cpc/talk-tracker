# talk-tracker — Build Plan

Status: draft v1 (2026-10-06). Owner: Fermilab DM & DE group (`fnal-cpc/talk-tracker`).

## 1. Goal

Find talks given by members of the Fermilab Dark Matter & Dark Energy group (and affiliated postdocs/students) at physics and astronomy colloquia and seminars across ~50 research institutions, and produce a monthly list in the format used by the group's monthly reports:

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
| Matching | Full-name match against roster variants; weak matches flagged, never silently accepted | Name collisions (Hsu, Newman, Pai, Lapi, Gaido) seen in literature search |
| "Invited" | Derived from series type (colloquium/seminar ⇒ invited) | Satisfies the report's requirement to state why a talk is invited |
| LLM extraction | Optional adapter, off by default | Reduces per-site parser effort for bespoke HTML; adds cost and an API key |

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
├── roster/
│   └── roster.yaml                # members, affiliates, name variants, ORCIDs
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
│   │   ├── indico.py              # Indico HTTP export API
│   │   ├── rss.py                 # RSS/Atom event feeds
│   │   ├── html.py                # CSS-selector-configured HTML scraping
│   │   ├── browser.py             # Playwright for JS-rendered pages (optional)
│   │   └── llm.py                 # LLM structured extraction (optional)
│   ├── parse.py                   # split "Speaker (Affil): Title" strings, date handling
│   ├── archive.py                 # upsert into data/events/*.jsonl, dedupe
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
    type: colloquium            # colloquium | seminar | lecture | conference | other
    invited: true               # default derived from type; override if needed
    url: https://...            # human-facing page (evidence link)
    adapter: localist           # ical | localist | tribe | indico | rss | html | browser | llm
    params:                     # adapter-specific
      base_url: https://...
      group: physics
      keyword: colloquium
    domains: [events.uchicago.edu]
    keeps_past_events: unknown  # true | false | unknown (determined during survey)
    active: true
    notes: ""
```

`talk-tracker domains` prints the union of all `domains` (for the network allowlist and for the fetcher's own allowlist).

### 4.2 Roster

```yaml
- id: drlica-wagner
  name: Alex Drlica-Wagner
  variants: ["Alex Drlica-Wagner", "Alexander Drlica-Wagner", "A. Drlica-Wagner"]
  orcid: 0000-0001-8251-933X
  role: member                  # member | joint | former | postdoc | student
  collisions: []                # known other people with similar names
- id: hsu
  name: Lauren Hsu
  variants: ["Lauren Hsu", "L. Hsu"]
  orcid: 0000-0002-5591-6433
  role: member
  collisions: ["Li-Ta Hsu", "Liang-Ching Hsu"]
```

Generated initially from the project's "Group Members" doc; maintained by hand thereafter.

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
| `indico` | `/export/categ/<id>.json?from=&to=&detail=contributions` | Labs and conferences; some categories need auth |
| `rss` | RSS/Atom | Fallback for feeds without dates in structured form |
| `html` | CSS selectors in `params` | For static pages; selectors for item, date, speaker, title, link |
| `browser` | Playwright + `html` selectors | JS-rendered pages; Chromium already available |
| `llm` | page text → JSON via an LLM API | Only for pages where selectors are impractical; requires API key; output validated against schema |

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
- Known collisions in the roster force downgrade to low unless the affiliation matches.

### 5.6 Report (`report.py`)
`talk-tracker report --month 2026-09` produces markdown:
```
* Invited Talks:
  * Alex Drlica-Wagner, Colloquium, Physics Colloquium, University X — 2026-09-12 [high] <url>
* Needs review:
  * ...
```
plus a coverage footer: number of series checked, number failing, number with no events in the month.

### 5.7 Health (`health.py`)
`talk-tracker check` reports, per series: last successful fetch, event count over last 90 days, failures. Flags series with zero events for 60+ days during term time (likely moved feeds).

### 5.8 CLI
```
talk-tracker validate                      # schema-check registry and roster
talk-tracker domains                       # print allowlist domains
talk-tracker scrape [--series ID] [--from DATE --to DATE] [--cache]
talk-tracker report --month YYYY-MM [--min-confidence medium]
talk-tracker check                         # feed health
talk-tracker backfill --from DATE          # one-off: pull archives where available
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
| M0 | Skeleton | package, CLI stub, models, CI, schema, roster file | `pytest` and `talk-tracker validate` pass in CI |
| M1 | Pilot survey | 10 institution YAMLs; survey table (series, platform, feed, past-event retention) | Every pilot series has an adapter assignment or is marked `unsupported` with a reason |
| M2 | Adapters | `ical`, `localist`, `tribe`, `indico`, `html` with fixtures and tests | All pilot series with feeds fetch successfully against fixtures; live where the domain is reachable |
| M3 | Archive + matching | `archive.py`, `match.py`, `parse.py` | Re-running scrape is idempotent; matcher passes collision tests (Hsu, Newman, Pai, Lapi, Gaido) |
| M4 | Report + validation | `report`, `backfill`, `check` | Backfill 12 months on pilot; compare against talks in previous reports; record recall and precision |
| M5 | Scale to ~50 | remaining registry entries; `browser`/`llm` adapters if needed | ≥ 80 % of registered series fetch successfully; documented list of unsupported series |
| M6 | Automation | `scrape.yml` weekly GitHub Action committing `data/`; failure notifications | Two consecutive unattended weeks without manual intervention |

## 8. Testing strategy
- **Fixtures**: every series gets saved responses in `tests/fixtures/` (captured once live or via manual download). Adapters are tested offline.
- **Parser golden tests**: title strings → expected (speaker, affiliation, title).
- **Matcher tests**: positive cases for each roster member; negative cases from known collisions.
- **Registry validation**: JSON Schema; domains present; no duplicate IDs.
- **Recall test (M4)**: a small YAML of known talks (from previous monthly reports) the backfill must find, where the venue is in the registry.

## 9. Operations
- **Development here (Claude workspace):** live fetching only for domains on the account's network allowlist; otherwise fixtures. Code is delivered as a git bundle and pushed to `fnal-cpc/talk-tracker` by a human.
- **Development locally / Actions:** no allowlist; full live runs.
- **Secrets:** none required for M0–M5 unless the `llm` adapter or authenticated Indico is used (then repository secrets).
- **Etiquette:** low request rates, robots.txt respected, weekly cadence; no scraping of login-protected pages.

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Pages drop past events | Weekly accumulation; `keeps_past_events` recorded; backfill where archives exist |
| Speaker not in a structured field | Title/abstract parsing; per-series patterns; LLM adapter as last resort |
| Feeds move or break each term | `check` command; failures logged per run; health section in report |
| Name collisions | Full-name matching, affiliation check, known-collision list, review section |
| JS-only calendars | Playwright adapter; mark `unsupported` if cost too high |
| Terms of use / robots.txt | Respect robots.txt; skip disallowed series; low rate |
| Conference talks not in seminar calendars | Indico adapter for conference categories; separate "conference" type, not auto-classified as invited |
| Coverage bias of institution list | Revisit list using venues from previous reports and recall misses |

## 11. Open questions
1. Final ~50 institution list (and whether to rank by field relevance rather than general rankings).
2. Include conferences (Indico) in v1, or seminars/colloquia only?
3. Is an LLM API key available for the optional extraction adapter?
4. Public or private repository (affects free Actions minutes and whether data is public).
5. Should affiliated students/postdocs' talks be reported, or only members'?
