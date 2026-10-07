# M1 pilot survey

Date: 2026-10-07.

**Method.** The first pass used web search and text extraction of the series pages
(Princeton and MIT pages were supplied by the group). It was done from a sandbox that could
not reach the sites. A group member then ran `talk-tracker probe` from a normal network on
2026-10-07, and the results were applied to the registry. A series is `verified: true` when
the probe reached its configured source: the feed returned events, or, for `html`, the
listing page loaded and no better feed was found. Remaining TBD ids are in each series'
`notes`.

Re-probe the unverified series with:

```sh
talk-tracker probe --unverified --json probe-results.json > probe-results.md
```

## Summary

* 10 institutions, 35 series: 20 colloquium, 13 seminar, 2 other (KIPAC tea talk,
  ITC luncheon; not counted as invited by default).
* **29 settled (24 verified sources, 5 `unsupported`), 6 awaiting re-probe.**
  * Verified structured sources (7): Indico ×2 (Fermilab JETP 241 events, CPC 55), iCal ×2
    (Caltech Astronomy series feed, Michigan Astronomy), PlanIt Purple ×1, Localist ×1
    (Stanford), The Events Calendar ×1 (LBNL RPM).
  * Verified `html` (17): the page loads and no event feed was found.
* Adapters: `html` 19, `unsupported` 5, `ical` 4, `planitpurple` 3, `indico` 2, `tribe` 1,
  `localist` 1.
* Past events: 33 series appear to keep past events; 2 unknown (Berkeley Physics, CfA).
* Platforms confirmed by the probe:
  * WordPress: Fermilab (no events API), LBNL RPM (The Events Calendar), MIT MKI (no events
    plugin), CIERA.
  * Drupal 10/11: KIPAC, SLAC, IAS, Princeton Astro, CfA.
  * Other platforms: LiveWhale (events.berkeley.edu), Open Berkeley, Localist
    (events.stanford.edu), PlanIt Purple, Happening @ Michigan, Indico (Fermilab, LBNL),
    the Caltech calendar CMS (series iCal feed `/calendar/ical?series=<id>`), and unbranded
    or static pages (UChicago, Berkeley cosmology, Michigan LITP).

## Decisions (2026-10-07)

1. **HTTP 403 for automated clients** (PLAN.md §0.7). Where another source exists for the
   same series, it is used: Michigan Physics uses events.umich.edu. Otherwise the series is
   `unsupported`: MIT Physics, Princeton Hamilton Colloquium, Princeton Astroparticle,
   Michigan HEP-Astro. The ITC Luncheon is unsupported and inactive, because the CfA says the
   lunches are not being held.
2. **robots.txt exception for public calendar feeds** (PLAN.md §0.8; `talk_tracker.policy`).
   Google Calendar public iCal and Outlook published-calendar URLs are fetched despite
   robots.txt. Harvard Physics therefore uses its public Google Calendar.
3. Per-event iCal links are not feeds. The Caltech physics pages offer only these, so the
   probe ignores one-event files when it suggests an adapter.

## Gaps and open items

| Item | Status |
|---|---|
| Caltech Physics Colloquium, TAPIR seminar | Find physics.caltech.edu series ids, then use `/calendar/ical?series=<id>` (works on the astro site). |
| Northwestern CIERA (2 series) | Program pages carry no PlanIt Purple link. Re-probe (the probe now checks the configured calendar); Astrophysics Seminar calendar id still TBD. |
| Michigan Physics colloquium | Source is `events.umich.edu/group/3804/ical` (page 403 is only the evidence link); re-probe. |
| Harvard Physics colloquium | Source is the public Google Calendar feed (robots exception); re-probe. |
| Michigan HEP-Astro seminar | Unsupported until its events.umich.edu group id is known. |
| Michigan cosmology seminar | Possible structured alternative: events.umich.edu group 5046 (LITP cosmology/astro seminars). |
| Berkeley Physics Colloquium | LiveWhale confirmed. Try LiveWhale `/live/ical/…` feeds in M2. |
| KIPAC (3 series) | Drupal pages reference Localist. Check for a KIPAC group on events.stanford.edu (structured data). |
| IAS astrophysics iCal feeds | Exist (`/ical/Astrophysics.ics`, …) but return 403; `html` used. |
| Stanford Physics Colloquium | Localist API confirmed; department filter id TBD (`/api/2/events/filters`). |
| MIT MKI Science Talks | Event-type slug TBD. |
| Harvard Astronomy department colloquium | Not identified separately from the CfA Colloquium. |

## Registry

Generated with `talk-tracker list`:

| series | institution | type | adapter | verified | keeps past | url |
|---|---|---|---|---|---|---|
| berkeley-physics-colloquium | UC Berkeley / Lawrence Berkeley National Laboratory | colloquium | html | yes | unknown | https://events.berkeley.edu/physics/all/search/Colloquia |
| berkeley-astronomy-colloquium | UC Berkeley / Lawrence Berkeley National Laboratory | colloquium | html | yes | true | https://astro.berkeley.edu/astronomy-colloquium |
| berkeley-cosmology-seminar | UC Berkeley / Lawrence Berkeley National Laboratory | seminar | html | yes | true | https://cosmology.lbl.gov/sem_bcg_future.html |
| berkeley-lbnl-rpm | UC Berkeley / Lawrence Berkeley National Laboratory | seminar | tribe | yes | true | https://rpm.physics.lbl.gov/ |
| caltech-physics-colloquium | California Institute of Technology | colloquium | html | no | true | https://physics.caltech.edu/events/seminar-calendar |
| caltech-astronomy-colloquium | California Institute of Technology | colloquium | ical | yes | true | https://www.astro.caltech.edu/calendar/filter?date_start=&date_end=&type=all&search=&past=0&mc=1&series=22 |
| caltech-tapir-seminar | California Institute of Technology | seminar | html | no | true | https://physics.caltech.edu/events/seminar-calendar |
| fnal-colloquium | Fermi National Accelerator Laboratory | colloquium | html | yes | true | https://events.fnal.gov/colloquium/ |
| fnal-jetp-seminar | Fermi National Accelerator Laboratory | seminar | indico | yes | true | https://theory.fnal.gov/jetp/ |
| fnal-cpc-seminar | Fermi National Accelerator Laboratory | seminar | indico | yes | true | https://astro.fnal.gov/events/seminars/ |
| harvard-physics-colloquium | Harvard University / Center for Astrophysics | colloquium | ical | no | true | https://www.physics.harvard.edu/colloq |
| harvard-cfa-colloquium | Harvard University / Center for Astrophysics | colloquium | html | yes | unknown | https://www.cfa.harvard.edu/node/9159 |
| harvard-itc-luncheon | Harvard University / Center for Astrophysics | other | unsupported | yes | true | https://itc.cfa.harvard.edu/luncheons |
| mit-physics-colloquium | Massachusetts Institute of Technology | colloquium | unsupported | yes | true | https://physics.mit.edu/events/david-and-edith-harris-physics-colloquium-series/ |
| mit-mki-astrophysics-colloquium | Massachusetts Institute of Technology | colloquium | html | yes | true | https://www.space.mit.edu/events/event-type/astrophysics-colloquium/ |
| mit-mki-science-talks | Massachusetts Institute of Technology | seminar | html | yes | true | https://www.space.mit.edu/events/ |
| northwestern-physics-astronomy-colloquium | Northwestern University | colloquium | planitpurple | yes | true | https://planitpurple.northwestern.edu/calendar/3758 |
| northwestern-ciera-interdisciplinary-colloquium | Northwestern University | colloquium | planitpurple | no | true | https://ciera.northwestern.edu/programs/interdisciplinary-colloquia/ |
| northwestern-ciera-astrophysics-seminar | Northwestern University | seminar | planitpurple | no | true | https://ciera.northwestern.edu/programs/astrophysics-seminars |
| princeton-ias-joint-astrophysics-colloquium | Princeton University / Institute for Advanced Study | colloquium | html | yes | true | https://web.astro.princeton.edu/events/colloquia |
| princeton-ias-astrophysics-seminars | Princeton University / Institute for Advanced Study | seminar | html | yes | true | https://www.ias.edu/sns/events/astrophysics |
| princeton-physics-colloquium | Princeton University / Institute for Advanced Study | colloquium | unsupported | yes | true | https://phy.princeton.edu/events/donald-r-hamilton-colloquium-series |
| princeton-astroparticle-seminar | Princeton University / Institute for Advanced Study | seminar | unsupported | yes | true | https://phy.princeton.edu/events |
| stanford-physics-colloquium | Stanford University / SLAC / KIPAC | colloquium | localist | yes | true | https://events.stanford.edu/department/applied_physicsphysics_colloquium |
| stanford-kipac-astrophysics-colloquium | Stanford University / SLAC / KIPAC | colloquium | html | yes | true | https://kipac.stanford.edu/events/astrophysics-colloquium-0 |
| stanford-kipac-seminar | Stanford University / SLAC / KIPAC | seminar | html | yes | true | https://kipac.stanford.edu/events/kipac-seminar-0 |
| stanford-kipac-tea-talk | Stanford University / SLAC / KIPAC | other | html | yes | true | https://kipac.stanford.edu/events/kipac-tea-talk-0 |
| stanford-slac-colloquium | Stanford University / SLAC / KIPAC | colloquium | html | yes | true | https://colloquium.slac.stanford.edu/upcoming-events |
| uchicago-physics-colloquium | University of Chicago | colloquium | html | yes | true | https://physics.uchicago.edu/events/category/colloquia-and-lectures/ |
| uchicago-astro-colloquia | University of Chicago | colloquium | html | yes | true | https://astrophysics.uchicago.edu/events/category/colloquia/ |
| uchicago-astro-seminars | University of Chicago | seminar | html | yes | true | https://astrophysics.uchicago.edu/events/category/seminars |
| umich-physics-colloquium | University of Michigan | colloquium | ical | no | true | https://lsa.umich.edu/physics/news-events/seminars-colloquia/department-colloquia.html |
| umich-astronomy-colloquium | University of Michigan | colloquium | ical | yes | true | https://lsa.umich.edu/physics/news-events/seminars-colloquia/astronomy-colloquia.html |
| umich-hep-astro-seminar | University of Michigan | seminar | unsupported | yes | true | https://lsa.umich.edu/physics/news-events/seminars-colloquia/hep-astro-seminars.html |
| umich-cosmology-seminar | University of Michigan | seminar | html | yes | true | https://lsa.umich.edu/litp/news-events/all-events/seminars/um-cosmology-group-seminars.html |
