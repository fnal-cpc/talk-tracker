# talk-tracker

Finds talks given by members of a research group at physics and astronomy colloquia and
seminars, by reading the public calendars of seminar series, and produces a monthly
"Invited Talks" list. See [PLAN.md](PLAN.md) for the design and milestones.

Status: **M1 (pilot survey)**. The registry lists 32 series at 10 institutions, all still
unverified (see [docs/survey.md](docs/survey.md)). `validate`, `domains`, `list` and `probe`
work; `scrape`, `report`, `check`, `backfill` and `evaluate` are stubs that exit with
status 2.

## Install

```sh
pip install -e '.[dev]'
pytest
```

Requires Python ≥ 3.11.

## Usage

```sh
talk-tracker validate                          # check registry/institutions/*.yaml
talk-tracker validate --roster group.txt       # ...and a roster (prints counts only)
talk-tracker domains [--active-only]           # hosts the scraper will contact
talk-tracker list                              # registry as a markdown table
talk-tracker probe [--series ID] [--json out.json]  # detect platform/feeds (network)
```

`probe` fetches each series page and the feeds it finds, sequentially, at most one request
per host every 2 s, respecting `robots.txt`. It prints a table comparing the registry's
adapter with the suggested one (⚠ marks a disagreement).

The registry directory defaults to `./registry`; override with `--registry DIR` or
`$TALK_TRACKER_REGISTRY`.

## Registry

One YAML file per institution in `registry/institutions/`, named `<id>.yaml`, validated
against `registry/schema.json` (format in PLAN.md §4.1). Rules beyond the schema:

* series ids start with `<institution id>-` and are unique across the registry;
* every `http(s)` URL inside `params` must be on a host listed in that series' `domains`
  (the fetcher refuses unlisted hosts);
* `adapter: unsupported` requires a reason in `notes`;
* `invited` defaults to true for `colloquium`, `seminar` and `lecture`, false for `other`.

## Rosters (people data)

**No roster is stored in this repository.** It is supplied at run time with `--roster PATH`
(`-` for stdin), either as the group's "Group Members" text (bulleted names under headings
such as `Current Group Members:`, `Joint Appointments:`, `Affiliated Postdocs:`,
`Affiliated Students:`, `Former Members:`, `Known Name Conflicts:`) or as YAML/JSON
(PLAN.md §4.2). `.gitignore` excludes `roster*`, `*.roster.*`, `members*` and
`known_talks*` files, and `tests/test_no_people_data.py` fails if a checksum-valid ORCID iD
other than the fictional test ones appears in the repository.

Name variants are generated from the name as written: without initials, `Surname, Given`
order, and initial forms. The surname is taken to be the last token; compound surnames
written without a hyphen need explicit `variants` in a YAML roster.
