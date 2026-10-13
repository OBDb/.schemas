# Polling proposal: review notes

The [guide](polling.md) proposes one shared convention for classifying ordinary
polling needs. Its six intervals come from BMW 4-series development work; the
fleet examples test whether the written rules can explain other vehicle
definitions. They do not establish runtime performance or approve those
vehicles' proposed interval changes.

## Decisions proposed

| Decision | Proposed treatment | Why it needs an explicit rule |
| --- | --- | --- |
| Six labels and intervals | Preserve 0.25, 1, 5, 15, 60 and 300 seconds | Stable vocabulary for people, agents and later validation |
| Engine control on EVs | Include propulsion and charging energy response under the existing label | Traction current and power have no combustion engine but comparable monitoring needs |
| Mixed command responses | Use the shortest interval justified by an understood, retained ordinary-use signal | The command is polled once; slower companions inherit its interval |
| Provisional meanings | Record a provisional tier separately from decoding confidence, with `needs-review` status | A plausible intended use does not verify a decoder or vehicle support |
| Unknown quantities | Leave the proposed tier unresolved and preserve acquisition settings | Neither the existing interval nor a positive response establishes meaning |
| Static identity/discovery | Separate connection/setup or on-demand review | VINs and sensor IDs are not accumulated history simply because they change slowly |
| Noncanonical intervals | Review their purpose before changing them | Research or capacity constraints may justify a different schedule |
| Load and achieved cadence | Assess separately for a defined vehicle/profile | A category specifies requested cadence, not throughput or sensor refresh |

These rules can be reviewed and refined as documentation before any fleet
migration. The guide retains the name Engine control for compatibility;
renaming it to Powertrain and energy would be a separate convention decision.
Exception representation and validation also remain open: the proposal does not
introduce an ordinary prefix with a mismatching interval, or silently assign a
new schema field for exceptions.

## Reading the examples

[polling-classifications.json](examples/polling-classifications.json) contains
28 deliberately selected command records across Hyundai IONIQ 5, Nissan Leaf,
Toyota Prius and Prius Prime, Ford F-150, Audi Q7, and Volkswagen Golf. These are
boundary examples, not a random sample or an exhaustive fleet classification.

Each record identifies the repository, source commit, repository-relative file,
file SHA256, GitHub source URL, and command JSON pointer. The reviewed input is a
local snapshot of that source file. The hash identifies its exact bytes; source
URLs provide a retrieval location but were not fetched as part of this proposal.
Existing command/transport metadata and applicability flags are preserved as
review data. Every returned signal has an intrinsic-tier entry; the governing
signals and effective command interval are recorded separately. Requested-load
arithmetic counts the command once, irrespective of its number of signals.

`schema_version` versions the review-record format, not the OBDb signalset
schema. These records live under `docs/examples/` because they are documentation
metadata, whereas the repository's top-level `examples/` contains signalsets
validated against `signals.json`.

Review statuses are:

- `proposed`: a category follows the draft rules; it is not approval to modify
  the source repository.
- `needs-review`: evidence, intended use, or scheduling requires a decision.
  A credible intended meaning may have a provisional interval; an ambiguous
  quantity has a null interval.
- `discovery-review`: the request belongs to identity/setup policy rather than
  recurring measurement classification; the proposed interval is null.
- `research-override`: preserve a separate research acquisition plan. This
  status is available to future review records; the 28 selected records do not
  include a wholly raw research acquisition example.

`confidence_in_classification` describes confidence in the category reasoning.
It does not rate decoder validity or vehicle support. `review_requirement` may
also describe a condition under which an otherwise clear default would need to
be reconsidered.

## Boundary examples to review

| Records | Observation | Proposed result |
| --- | --- | --- |
| F01–F02 | Driving measurements appear in chassis and HVAC modules | Operational; module identity does not decide the tier |
| F03 | One BMS response contains motor speed, power, SOC, temperatures and lifetime counters | Provisional 0.25 s if motor speed is retained as driving feedback; review its fourfold request increase and long response |
| F04–F05 | SOC and charging-equipment states describe different quantities | Reserve/condition at 60 s; equipment state at 5 s |
| F07 | Tire sensor IDs are static metadata | Discovery review; no ordinary-tier proposal |
| F08–F10 | Traction current, SOH and odometer have different uses | 1 s, 60 s and 300 s; review the SOH increase from hourly to once per minute |
| F11–F14 | Mixed driving packets, oil temperature, battery cooling inlet and TPMS | Apply bundle precedence and explicit temperature/pressure boundaries |
| F15 | Hybrid SOC may be used for energy-management transitions | Provisional reserve-monitoring default 60 s; review intended use before slowing it |
| F16–F19 | Fuel trim, intake temperature, coolant and atmosphere | 1, 5, 15 and 60 s; words such as “short-term” or a common unit are insufficient |
| F20 | “Latest cycle” misfire count does not specify its counting window | Unresolved: establish live-window versus drive-cycle-history meaning |
| F21–F23, F27 | DPF pressure, temperature, distance since regeneration and soot load | Separate response, thermal, history and condition rules; retain decoding review where units are unknown |
| F24–F25 | Steering fields may be stored snapshots; regeneration time has questionable scaling | Unresolved; preserve source settings pending evidence |
| F26, F28 | Target/actual fuel pressure and resettable accumulated distance | Setpoint follows controlled quantity; resettable totals remain history |

The original BMW work also contains research commands with intended-use labels
before decoding is verified. This proposal separates those concepts rather than
making a prefix a universal verification marker. Hidden unknown companion bytes
likewise do not invalidate a command's independently understood measurements.

## Scope of this change

This change adds documentation and classification examples only. It does not
modify `signals.json`, formatters, runtime scheduling, CI policy, or vehicle
definitions. Existing intervals outside the six values remain schema-valid.
No response fixtures are fabricated, and no vehicle polling is performed.

Future conformance work should verify interval/prefix consistency, full command
coverage, explicit exceptions, and preservation of unrelated configuration.
Semantic correctness still needs review against the rules; prefix matching
alone cannot validate category choice or achieved cadence.
