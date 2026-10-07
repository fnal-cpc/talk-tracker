# M1 pilot survey

Date: 2026-10-07. Method: web search plus text extraction of the series pages, done from a
sandbox that could not reach the sites directly. **No feed has been fetched yet.** Every
series is therefore `verified: false`. To confirm each assignment, run the probe from a
machine with normal network access:

```sh
talk-tracker probe --json probe-results.json > probe-results.md
```

Then, for each series: confirm or correct `adapter` and `params`, fill in the missing ids
(marked TBD in `notes`), and set `verified: true`.

## Summary

* 10 institutions, 32 series: 18 colloquium, 12 seminar, 2 other (KIPAC tea talk,
  ITC luncheon; not counted as invited by default).
* Provisional adapters: `html` 19, `ical` 4, `tribe` 3, `planitpurple` 3, `indico` 2,
  `localist` 1. `html` is a placeholder for "no feed identified yet". Several of those
  pages run on Drupal or WordPress, or offer per-event iCal links, so the probe may find
  structured feeds for some of them.
* Past events: 30 series appear to keep past events (archive pages, past-event URLs,
  Indico, or feed archive parameters); 2 unknown (Berkeley Physics on
  events.berkeley.edu, CfA Colloquium).
* New adapter needed: **`planitpurple`** (Northwestern). It has a documented XML feed with
  date-range and 4-year archive parameters, which is better than scraping.
* Platforms seen: custom PSD events CMS (UChicago physics/astrophysics), WordPress
  (Fermilab, LBNL RPM, MIT MKI; The Events Calendar on the last two), Indico (Fermilab),
  PlanIt Purple (Northwestern), Localist (Stanford central calendar), Drupal 10/11
  (KIPAC, SLAC, IAS, CfA, Harvard Physics), Open Berkeley, Caltech division-calendar CMS,
  Google Calendar (Harvard Physics), Happening @ Michigan (events.umich.edu: JSON/RSS/iCal),
  hand-written static HTML (Berkeley cosmology seminar).
* researchseminars.org mirrors some series with an iCal export (e.g. Fermilab JETP). It
  is worth checking for other series at M5.

## Gaps and open items

| Item | Status |
|---|---|
| Princeton Physics Colloquium | Series page not found by search; not registered. |
| MIT Physics Colloquium | Series page not found by search; not registered. |
| Harvard Astronomy department colloquium | Not identified separately from the CfA Colloquium. |
| Caltech Physics Colloquium, TAPIR seminar | Listing is shared with other series; series filter ids TBD. |
| Northwestern CIERA Astrophysics Seminar | PlanIt Purple calendar id TBD. |
| Michigan HEP-Astro seminar | Happening @ Michigan group id TBD. |
| MIT MKI series | Same calendar; The Events Calendar category slugs TBD. |
| Berkeley Physics Colloquium | Platform of events.berkeley.edu (LiveWhale vs. Localist) TBD. |
| Stanford Physics Colloquium | Localist department filter id TBD (`/api/2/events/filters`). |
| Feed URLs constructed from documented patterns (Harvard Google Calendar ICS, Michigan `/group/<id>/ical`) | Not fetched; the probe checks them. |
| Text-extraction staleness | Some fetched pages returned months-old content, so the dates in `notes` are illustrative only. |

## Registry

Generated with `talk-tracker list`:

| series | institution | type | adapter | verified | keeps past | url |
|---|---|---|---|---|---|---|
| berkeley-physics-colloquium | UC Berkeley / Lawrence Berkeley National Laboratory | colloquium | html | no | unknown | https://events.berkeley.edu/physics/all/search/Colloquia |
| berkeley-astronomy-colloquium | UC Berkeley / Lawrence Berkeley National Laboratory | colloquium | html | no | true | https://astro.berkeley.edu/astronomy-colloquium |
| berkeley-cosmology-seminar | UC Berkeley / Lawrence Berkeley National Laboratory | seminar | html | no | true | https://cosmology.lbl.gov/sem_bcg_future.html |
| berkeley-lbnl-rpm | UC Berkeley / Lawrence Berkeley National Laboratory | seminar | tribe | no | true | https://rpm.physics.lbl.gov/ |
| caltech-physics-colloquium | California Institute of Technology | colloquium | html | no | true | https://physics.caltech.edu/events/seminar-calendar |
| caltech-astronomy-colloquium | California Institute of Technology | colloquium | html | no | true | https://www.astro.caltech.edu/calendar/filter?date_start=&date_end=&type=all&search=&past=0&mc=1&series=22 |
| caltech-tapir-seminar | California Institute of Technology | seminar | html | no | true | https://physics.caltech.edu/events/seminar-calendar |
| fnal-colloquium | Fermi National Accelerator Laboratory | colloquium | html | no | true | https://events.fnal.gov/colloquium/ |
| fnal-jetp-seminar | Fermi National Accelerator Laboratory | seminar | indico | no | true | https://theory.fnal.gov/jetp/ |
| fnal-cpc-seminar | Fermi National Accelerator Laboratory | seminar | indico | no | true | https://astro.fnal.gov/events/seminars/ |
| harvard-physics-colloquium | Harvard University / Center for Astrophysics | colloquium | ical | no | true | https://www.physics.harvard.edu/colloq |
| harvard-cfa-colloquium | Harvard University / Center for Astrophysics | colloquium | html | no | unknown | https://www.cfa.harvard.edu/node/9159 |
| harvard-itc-luncheon | Harvard University / Center for Astrophysics | other | html | no | true | https://itc.cfa.harvard.edu/luncheons |
| mit-mki-astrophysics-colloquium | Massachusetts Institute of Technology | colloquium | tribe | no | true | https://space.mit.edu/events/ |
| mit-mki-science-talks | Massachusetts Institute of Technology | seminar | tribe | no | true | https://space.mit.edu/events/ |
| northwestern-physics-astronomy-colloquium | Northwestern University | colloquium | planitpurple | no | true | https://planitpurple.northwestern.edu/calendar/3758 |
| northwestern-ciera-interdisciplinary-colloquium | Northwestern University | colloquium | planitpurple | no | true | https://ciera.northwestern.edu/programs/interdisciplinary-colloquia/ |
| northwestern-ciera-astrophysics-seminar | Northwestern University | seminar | planitpurple | no | true | https://ciera.northwestern.edu/programs/astrophysics-seminars |
| princeton-ias-joint-astrophysics-colloquium | Princeton University / Institute for Advanced Study | colloquium | html | no | true | https://www.ias.edu/sns/astrophysics/joint-iaspu-astrophysics-colloquium |
| princeton-ias-astrophysics-seminars | Princeton University / Institute for Advanced Study | seminar | html | no | true | https://www.ias.edu/sns/events/astrophysics |
| stanford-physics-colloquium | Stanford University / SLAC / KIPAC | colloquium | localist | no | true | https://events.stanford.edu/department/applied_physicsphysics_colloquium |
| stanford-kipac-astrophysics-colloquium | Stanford University / SLAC / KIPAC | colloquium | html | no | true | https://kipac.stanford.edu/events/astrophysics-colloquium-0 |
| stanford-kipac-seminar | Stanford University / SLAC / KIPAC | seminar | html | no | true | https://kipac.stanford.edu/events/kipac-seminar-0 |
| stanford-kipac-tea-talk | Stanford University / SLAC / KIPAC | other | html | no | true | https://kipac.stanford.edu/events/kipac-tea-talk-0 |
| stanford-slac-colloquium | Stanford University / SLAC / KIPAC | colloquium | html | no | true | https://colloquium.slac.stanford.edu/upcoming-events |
| uchicago-physics-colloquium | University of Chicago | colloquium | html | no | true | https://physics.uchicago.edu/events/category/colloquia-and-lectures/ |
| uchicago-astro-colloquia | University of Chicago | colloquium | html | no | true | https://astrophysics.uchicago.edu/events/category/colloquia/ |
| uchicago-astro-seminars | University of Chicago | seminar | html | no | true | https://astrophysics.uchicago.edu/events/category/seminars |
| umich-physics-colloquium | University of Michigan | colloquium | ical | no | true | https://lsa.umich.edu/physics/news-events/seminars-colloquia/department-colloquia.html |
| umich-astronomy-colloquium | University of Michigan | colloquium | ical | no | true | https://lsa.umich.edu/physics/news-events/seminars-colloquia/astronomy-colloquia.html |
| umich-hep-astro-seminar | University of Michigan | seminar | ical | no | true | https://lsa.umich.edu/physics/news-events/seminars-colloquia/hep-astro-seminars.html |
| umich-cosmology-seminar | University of Michigan | seminar | html | no | true | https://lsa.umich.edu/litp/news-events/all-events/seminars/um-cosmology-group-seminars.html |
