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
* **24 verified, 11 not.**
  * Verified structured sources (7): Indico ×2 (Fermilab JETP 241 events, CPC 55), iCal ×2
    (Caltech Astronomy series feed, Michigan Astronomy), PlanIt Purple ×1, Localist ×1
    (Stanford), The Events Calendar ×1 (LBNL RPM).
  * Verified `html` (17): the page loads and no event feed was found.
* Adapters: `html` 23, `ical` 5, `planitpurple` 3, `indico` 2, `tribe` 1, `localist` 1.
* Past events: 33 series appear to keep past events; 2 unknown (Berkeley Physics, CfA).
* Platforms confirmed by the probe:
  * WordPress: Fermilab (no events API), LBNL RPM (The Events Calendar), MIT MKI (no events
    plugin), CIERA.
  * Drupal 10/11: KIPAC, SLAC, IAS, Princeton Astro, CfA.
  * Other platforms: LiveWhale (events.berkeley.edu), Open Berkeley, Localist
    (events.stanford.edu), PlanIt Purple, Happening @ Michigan, Indico (Fermilab, LBNL),
    the Caltech calendar CMS (series iCal feed `/calendar/ical?series=<id>`), and unbranded
    or static pages (UChicago, Berkeley cosmology, Michigan LITP).

## Probe findings that need a decision

1. **HTTP 403 for automated clients.** Six series pages refused the probe:
   * Harvard Physics and the ITC luncheon;
   * MIT Physics;
   * both Princeton Physics series;
   * Michigan Physics and HEP-Astro.

   The probe identifies itself and sends normal `Accept` headers (added after this run). If
   these pages still refuse it, the options are:
   * the `browser` adapter (headless Chromium);
   * an alternative source for the same series, e.g. the events.umich.edu group feed, which
     did work for Michigan Astronomy;
   * `unsupported`.
2. **Google Calendar and robots.txt.** calendar.google.com disallows its public iCal URLs
   in robots.txt (seen for LBNL RPM). Harvard Physics' only machine-readable source is a
   Google Calendar. Calendar clients routinely fetch these feeds, but the plan says we
   respect robots.txt. Either make an explicit exception for public calendar feeds, or
   leave Harvard Physics unsupported.
3. **Per-event iCal links are not feeds.** The Caltech physics pages offer only per-event
   `?ical` links. The probe now ignores one-event files when it suggests an adapter.

## Gaps and open items

| Item | Status |
|---|---|
| Caltech Physics Colloquium, TAPIR seminar | Find physics.caltech.edu series ids, then use `/calendar/ical?series=<id>` (works on the astro site). |
| Northwestern CIERA (2 series) | Program pages carry no PlanIt Purple link. Re-probe (the probe now checks the configured calendar); Astrophysics Seminar calendar id still TBD. |
| Michigan Physics colloquium | Page 403. Configured feed `events.umich.edu/group/3804/ical` not yet checked; re-probe. |
| Michigan HEP-Astro seminar | Page 403; events.umich.edu group id TBD. |
| Berkeley Physics Colloquium | LiveWhale confirmed. Try LiveWhale `/live/ical/…` feeds in M2. |
| KIPAC (3 series) | Drupal pages reference Localist. Check for a KIPAC group on events.stanford.edu (structured data). |
| IAS astrophysics iCal feeds | Exist (`/ical/Astrophysics.ics`, …) but return 403; `html` used. |
| Stanford Physics Colloquium | Localist API confirmed; department filter id TBD (`/api/2/events/filters`). |
| MIT MKI Science Talks | Event-type slug TBD. |
| Princeton Astroparticle Seminar | Series URL TBD (phy.princeton.edu returns 403). |
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
| harvard-itc-luncheon | Harvard University / Center for Astrophysics | other | html | no | true | https://itc.cfa.harvard.edu/luncheons |
| mit-physics-colloquium | Massachusetts Institute of Technology | colloquium | html | no | true | https://physics.mit.edu/events/david-and-edith-harris-physics-colloquium-series/ |
| mit-mki-astrophysics-colloquium | Massachusetts Institute of Technology | colloquium | html | yes | true | https://www.space.mit.edu/events/event-type/astrophysics-colloquium/ |
| mit-mki-science-talks | Massachusetts Institute of Technology | seminar | html | yes | true | https://www.space.mit.edu/events/ |
| northwestern-physics-astronomy-colloquium | Northwestern University | colloquium | planitpurple | yes | true | https://planitpurple.northwestern.edu/calendar/3758 |
| northwestern-ciera-interdisciplinary-colloquium | Northwestern University | colloquium | planitpurple | no | true | https://ciera.northwestern.edu/programs/interdisciplinary-colloquia/ |
| northwestern-ciera-astrophysics-seminar | Northwestern University | seminar | planitpurple | no | true | https://ciera.northwestern.edu/programs/astrophysics-seminars |
| princeton-ias-joint-astrophysics-colloquium | Princeton University / Institute for Advanced Study | colloquium | html | yes | true | https://web.astro.princeton.edu/events/colloquia |
| princeton-ias-astrophysics-seminars | Princeton University / Institute for Advanced Study | seminar | html | yes | true | https://www.ias.edu/sns/events/astrophysics |
| princeton-physics-colloquium | Princeton University / Institute for Advanced Study | colloquium | html | no | true | https://phy.princeton.edu/events/donald-r-hamilton-colloquium-series |
| princeton-astroparticle-seminar | Princeton University / Institute for Advanced Study | seminar | html | no | true | https://phy.princeton.edu/events |
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
| umich-hep-astro-seminar | University of Michigan | seminar | ical | no | true | https://lsa.umich.edu/physics/news-events/seminars-colloquia/hep-astro-seminars.html |
| umich-cosmology-seminar | University of Michigan | seminar | html | yes | true | https://lsa.umich.edu/litp/news-events/all-events/seminars/um-cosmology-group-seminars.html |
