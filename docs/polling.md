# Proposed polling categories

This proposal defines six ordinary-use polling categories for OBDb contributors
and agents. It includes classification rules, command-bundle handling, and
worked examples across combustion, hybrid, and electric vehicles. It does not
change `signals.json`, enforce new intervals, or modify vehicle definitions.

The categories originated in a BMW 4-series development snapshot
(`M2ABRAMSTANK/BMW-4-series`, commit
`bb2381d9a2322c850e269b80bbb4e1bd39dc1c5a`). The fleet extensions here are proposed
policy, not a claim of measured vehicle timing or established OBDb-wide practice.
See [review notes](polling-review.md) for the policy decisions and scope, and
[worked classification records](examples/polling-classifications.json) for
source-pinned examples.

## Representation and scope

The existing [signalset schema](../signals.json) expresses requested polling
intervals in the command-level `freq` field. This proposal documents the category
with a `[Polling: <exact label>] ` prefix on each signal description in the
command. Preserve any existing description after that prefix. An example is
`[Polling: Thermal condition] Engine coolant temperature.` with `freq: 15` on
the command. These prefixes are documentation; clients continue to use `freq`.
No new inline fields or mandatory schema constraints are introduced.

Only apply a proposed category after review. Existing research schedules,
noncanonical intervals, applicability filters, and debug status remain unchanged
by this documentation. Classification confidence and decoding confidence belong
in separate review records; a tier label does not establish vehicle support.

## Quick reference

Choose the category from the measurement's ordinary use. Then choose one
interval for the whole request using the bundle rule below. `freq` means the
requested interval **in seconds**, despite its name; a smaller number requests
more frequent reads. It does not specify hertz, sensor update rate, or achieved
cadence.

| Exact label | `freq` (s) | Requests/minute per command | Ordinary use | Typical examples |
| --- | ---: | ---: | --- | --- |
| Operational | 0.25 | 240 | Immediate driving feedback: motion and driver input | Vehicle/wheel speed, RPM, steering angle, accelerator/brake position, actual gear |
| Engine control | 1 | 60 | Powertrain and energy response under changing demand | Boost, rail pressure, lambda, fuel trims, engine load, traction current/power, motor torque |
| Short-term trends | 5 | 12 | Near-term electrical, intake, and equipment-state trends | Auxiliary voltage/current, intake temperature, HVAC output state, door/lock/charge state |
| Thermal condition | 15 | 4 | Warm-up and sustained component temperature | Coolant, engine/transmission oil, traction battery, motor, inverter temperature |
| Health and environment | 60 | 1 | Slowly changing condition, reserves, and surroundings | TPMS, ambient temperature, barometric pressure, fuel level, SOC, range, SOH |
| Cumulative history | 300 | 0.2 | Totals, historical records, and persistent learned values | Odometer, lifetime energy/fuel, operating hours, accumulated cycles, learned adaptations |

These are ordinary monitoring defaults. They do not promise capture of every
transition or suitability for a control loop. A special diagnostic experiment
may need a different interval; keep its exception separate from ordinary tier
classification.

## Category rules and boundaries

### 1. Operational — 0.25 seconds

Use for measurements whose ordinary purpose is a responsive view of driving
motion or driver input. Include vehicle and wheel speeds, engine RPM, driving
motor RPM, steering angle, longitudinal/lateral acceleration, pedal position,
brake switch/pressure used as driving feedback, and actual selected gear.

BMW anchors: RPM `224807`, speed `224AB1`, wheel speeds `22DBE4`. The command's
module does not decide the category: a speed signal from an HVAC or cluster
module still belongs here. Engine load, commanded torque, and combustion
feedback belong in Engine control by default. A parked-door state is not
Operational just because it can change suddenly; its default use is a state
display, covered by Short-term trends.

### 2. Engine control — 1 second

Use for instantaneous powertrain response to changing load or energy demand:
boost/manifold pressure, rail pressure, lambda/air-fuel ratio, fuel trim, air
mass flow, engine load, torque demand/delivery, injection quantity, instantaneous
fuel rate, and powertrain actuator feedback.

For fleet use, **extend the meaning of this existing label to electric and
hybrid propulsion and charging energy response**: traction battery current,
traction/charging voltage and power, inverter electrical output, and motor
torque. Keep the exact label for compatibility. A future rename to “Powertrain
and energy” would require a coordinated change to documentation and label tests;
this draft does not perform that migration.

BMW anchors: boost `224205`/`224AB0`, rail pressure `2256D7`, lambda `225889`.
RPM remains Operational. Component temperature remains Thermal condition.
Auxiliary 12 V supply monitoring remains Short-term trends. Total energy
consumed remains Cumulative history. SOC is a reserve, not instantaneous power.

### 3. Short-term trends — 5 seconds

Use for short trend monitoring without immediate driving-feedback requirements:
auxiliary battery voltage/current, intake/charge-air temperature in ordinary
monitoring, blower/compressor output or cabin setpoint, and present equipment
states such as doors, locks, HVAC mode, charging enabled, or regeneration active.

BMW anchors: IBS supply `225853`, intake temperature `22580F`. Charge state
(charging/not charging) is a state; charge current is Engine control; SOC is
Health and environment. A present regeneration flag is a state; accumulated
regenerations are history. Cabin air/outlet temperature used for HVAC response
fits here; outside ambient temperature belongs in Health and environment.

For EV cell-balance/voltage-dispersion trend observation, use 5 s for individual
cell voltages, extrema, and associated cell indices. This is a proposed
use-specific default; total traction pack voltage under load remains 1 s and
long-term battery SOH remains 60 s. Main contactor, ignition, and plug states used
as equipment-state displays default to 5 s; transient switching experiments
need an explicit acquisition requirement.

Body and charging-state defaults are an extension beyond the original BMW
examples. If the intended application must detect a shorter event, record that
requirement and review an exception; do not silently classify every boolean at
0.25 seconds. Polling at 5 seconds can miss a shorter transition.

### 4. Thermal condition — 15 seconds

Use for component warm-up and sustained operating temperature: engine coolant,
engine/transmission oil, traction battery cells/modules, motor, inverter,
catalyst and exhaust temperature in ordinary thermal monitoring.

BMW anchors: coolant `224300`/`225805`, oil `224408`/`225822`, transmission
`22DA12`. Celsius alone is insufficient: intake temperature defaults to 5 s,
ambient to 60 s, and tire temperature to 60 s alongside TPMS condition reporting.
Battery cooling inlet temperature follows component thermal conditioning at
15 s; “intake” alone does not invoke the combustion intake-air 5 s exception.
Special transient combustion, regeneration, or charging studies can require
faster sampling, with an explicit use-case exception rather than an inference
from sensor name alone.

### 5. Health and environment — 60 seconds

Use for periodic condition, reserves, and environmental context: tire pressure
and temperature, atmospheric pressure, ambient temperature, fuel/DEF level,
traction or auxiliary SOC, remaining range, battery SOH/capacity estimate,
isolation resistance, soot/ash loading, readiness and persistent fault status.

BMW anchors: tire commands `22DC98`–`22DC9B`, atmospheric pressure `224201`.
Distinguish a stored fault/readiness status from a live fault event needed by a
specific application. Distinguish remaining range from vehicle speed, capacity
from instantaneous power, and SOH from cumulative energy throughput. A pressure
is not inherently a 60-second reading: boost and rail pressure default to 1 s;
braking feedback defaults to 0.25 s.

### 6. Cumulative history — 300 seconds

Use for values whose ordinary meaning is an accumulated total, historical
summary, or persistent learned record: distance traveled, lifetime and trip
fuel/energy, engine run time, charge cycles, fault occurrence counts, stored
freeze-frame/history values, and learned adaptations. Session/trip counters
can reset and still be history. Record reset behavior; do not mistake a
counter's numeric change each second for a need to poll each second.

BMW anchors: odometers `22D10D`, accumulated driving-mode-time bundle `22DA37`.
Instantaneous fuel flow, remaining fuel, and total fuel consumed belong to
Engine control, Health and environment, and Cumulative history respectively.
A rolling live event count used to detect short events needs a documented
use-case review, rather than automatic classification from the word “count.”

VINs, serial numbers, firmware versions, supported-PID discovery, and immutable
calibration identifiers normally belong to connection/setup or on-demand
discovery, outside recurring measurement polling. Do not invent a seventh tier
or silently force them into 300 s. If an existing client repeatedly polls them,
leave that behavior unchanged in the dry run and flag a discovery-policy
decision. Do not confuse a learned adaptation value with a static identifier.

## Decision procedure

1. **Establish identity and applicability.** Read the complete request, its
   route, response addresses, inherited defaults, filters, signals, descriptions,
   and available evidence. Identify what each field measures. A PID number,
   module, unit, name keyword, or existing interval alone cannot establish its
   category. A positive response alone cannot establish a field's meaning.
2. **Handle uncertainty and discovery first.** If the intended quantity is
   unknown or competing hypotheses imply different tiers, leave the tier
   unresolved. Retain existing research intervals, prefixes, and gates. A
   credible but unverified intended meaning may receive a provisional category
   in the review report, with `needs-review` status; this does not establish
   decoding or vehicle support. Existing commands labeled
   `[Polling: Unclassified; research override]` keep their prefix until their project explicitly decides
   how provisional tiers are represented. For a new uncertain request, require
   a separate research acquisition plan; this guide supplies no default research
   interval. Put identity/discovery reads in a separate review status.
3. **Assign each understood signal an intrinsic category** using the six rules
   above. This is a review annotation, not a new signalset field. Existing
   maintained decoder documentation can support a proposed classification;
   record the evidence level without claiming new vehicle validation.
4. **Resolve the command as a bundle (proposed fleet rule).** Select the shortest
   interval required by
   any understood signal with an ordinary monitoring use. Record the signal
   that determines the interval. All signals in that command, including hidden,
   static, historical, and unknown companion fields, inherit the selected
   command prefix and interval. Do not describe inheritance as proof of an
   unknown field's meaning. If no ordinary signal justifies the command,
   retain research/discovery review status.
5. **Separate scheduling from classification.** Check byte/frame size, route
   overhead, enabled-command count, ECU/adapter throughput, retries, and
   duplicate sources. A correct category can still request more traffic than
   the vehicle/client can deliver. Flag capacity issues; do not change a label
   simply to fit a budget or silently remove a bundled signal.
6. **Record the proposed change or hold.** Keep current and proposed values
   separate, cite the rule and evidence, record assumptions and affected
   model-year/variant filters, and require review of unresolved cases.

When more than one rule seems plausible, resolve measurement meaning first:
current motion/input → Operational; instantaneous powertrain response → Engine
control; equipment state/auxiliary or intake trend → Short-term trends;
component thermal state → Thermal condition; reserve/condition/environment →
Health and environment; accumulated/learned/history → Cumulative history.
The explicit exceptions in the category descriptions take precedence over a
generic keyword. If meaning or intended use remains ambiguous, hold the record
for review rather than guessing or selecting the fastest category as a fallback.

## Bundles, duplicates, and exceptions

**A command is the scheduling unit.** One response may include RPM, coolant,
SOC, and lifetime energy. Its intrinsic categories differ, but a retained RPM
measurement drives a 0.25 s command interval and every description receives
`[Polling: Operational]`. The slower fields are read as companions. Do not split
the request into several copies to assign per-signal intervals.

Hidden status does not decide eligibility or category. A hidden unknown TPMS
byte may inherit a known tire-pressure command's 60 s interval. An entirely
unknown debug request does not become verified because its interval happens to
equal a canonical value. Debug status also does not automatically make a known
measurement unknown: availability/validation, category, and research schedule
are separate decisions. Preserve existing `dbg`, year filters, staging groups,
and routing throughout classification.

Duplicated measurements keep the same intrinsic category. A command that is
the only route to a required slow field may also contain a redundant fast field;
under the proposed bundle rule it still receives the fast interval. Selecting a
preferred source or excluding the redundant fast field from an acquisition
profile is a separate, explicit optimization. Document it before relying on a
slower bundle interval. Do not introduce conflicting exceptions by accident.

An ordinary-use exception record must give the canonical category/default,
requested alternative interval, reason/use case, scope, evidence, owner, and
review condition. Do not add new tier names or emit an ordinary label with a
nonmatching `freq` under the existing BMW convention. Until an exception
representation and validator are agreed, hold such changes for review. Research
overrides already have their separate representation and are not a seventh
ordinary tier.

## Human and agent workflow

Setpoints follow their controlled quantity when used for comparison: target
boost is 1 s, target tire pressure is 60 s, and cabin temperature setpoint is
5 s under the HVAC-response rule. A stored calibration constant instead needs
the discovery/static-data review described above.

Synthetic/derived signals have no independent read request. Classify their
intended use, identify each input command, and review input freshness and time
alignment. Do not add a command for the synthetic expression or automatically
accelerate a stable denominator such as battery capacity to match live energy.
Record any caching or synchronization assumptions for client/profile review.

Use this same sequence for an existing repository or a new PID set:

1. Freeze the source revision and relevant file hashes. For a fleet assignment,
   use one repository/project worktree per editing owner; parallel readers may
   share a frozen snapshot. Keep inherited/shared signal definitions explicit.
2. Inventory commands and signals. Use a file path plus command array index
   (JSON pointer) as a snapshot-unique location, with full command and route
   metadata for review. Bare PID or signal ID is not a fleet-unique key.
3. Produce a proposal record for every reviewed command: `proposed`,
   `needs-review`, `research-override`, or `discovery-review`. Record source,
   observed configuration, per-signal reasoning, the bundled result, and load
   implications. No unresolved record should be reported as classified.
4. Review representative hard cases together before distributing more repos:
   EV power/SOC, mixed fast/slow payloads, body state vs driving input,
   temperatures, counter resets, and unknown hidden fields. Two reviewers should
   be able to explain the same outcome from the written rules.
5. In a later authorized implementation, update only `freq` and the polling
   prefix of every description in each approved command. Preserve the rest of
   each description verbatim and preserve decoders, IDs, routing, filters,
   debug/staging behavior, and top-level budgets. Follow that repo's formatter.
6. Validate exact label/interval matching and complete coverage of every changed
   command, including fields missing descriptions. Check research exemptions
   independently. Run that repository's existing schema/fixture checks; inspect
   the diff for unrelated changes. Test success validates configuration, not
   real achieved cadence. Validate vehicle/client behavior separately before
   claiming capacity or timing guarantees.

This proposal supplies guidance for steps 1–4; implementation in steps 5–6 is
a separate repository change.
New definitions require their usual decoding/applicability evidence in addition
to polling classification. Shared definitions should be reviewed at their owner
and version; absence from a local JSON file is not proof they are absent at
runtime.

### Proposal record template

Store this review metadata in a separate report, never as new keys in an OBDb
signalset. Field names below form a suggested interchange contract for agents
and human review; they are not an OBDb JSON Schema extension.

```json
{
  "example_id": "illustration",
  "repository": "vehicle-repository",
  "source_commit": "full commit SHA",
  "source_sha256": "hash of reviewed bytes",
  "source_file": "signalsets/v3/default.json",
  "command_pointer": "/commands/0",
  "identity": {"hdr": "7E0", "rax": "7E8", "cmd": {"01": "0C"}},
  "availability_preserve": {},
  "observed_freq_seconds": 1,
  "status": "proposed",
  "confidence_in_classification": "high",
  "decoding_evidence_status": "existing definition; not independently validated here",
  "acquisition_status": "preserve source eligibility and research status",
  "signals": [
    {"id": "EXAMPLE_RPM", "intrinsic_tier": "Operational",
     "intrinsic_interval_seconds": 0.25,
     "inherits_faster_command_interval": false,
     "evidence": "Maintained definition identifies engine RPM",
     "rule": "1: immediate driving feedback"}
  ],
  "proposed_command_tier": "Operational",
  "proposed_freq_seconds": 0.25,
  "driving_signals": ["EXAMPLE_RPM"],
  "nominal_requests_per_minute": {"before": 60, "after": 240},
  "assumptions": ["Illustrative record; not a captured vehicle request"],
  "rationale": "RPM provides immediate driving feedback",
  "review_requirement": null,
  "owner": "reviewer/project"
}
```

Include every signal in a real record. Allow `intrinsic_tier: null` for an
unknown/discovery companion and explain inheritance. Use null proposed values
when quantity/use is unresolved or outside recurring polling. A `needs-review`
record can retain a provisional tier when the intended meaning is credible but
its evidence or scheduling needs review; it is not approved to apply. Retain
existing research schedules independently rather than manufacturing a default.
Also capture filters, debug status, inherited defaults, transport parameters,
and other applicability fields from the source, even when absent in this short
example. Record noncanonical current intervals exactly; never round to the
nearest tier to classify a request.

## Capacity review

For a selected enabled command set, nominal requested reads/minute are
`sum(60 / freq_seconds)`. Count each command once, not each returned signal.
Four independent Operational commands already request 960 reads/minute. Long
multi-frame responses can be more costly than short reads with the same interval.
The formula is an offered-load estimate, not measured bus occupancy or achieved
throughput; runtime filters, shared definitions, backoff, retries, support
discovery, and scheduler behavior can change it.

The BMW 400/min testing allowance is local research policy, excludes ordinary
polling in its documented use, and must not be copied as a fleet capacity limit.
Do not sum all stored fleet commands as if one vehicle polls them all. Compare
before/after only for a defined vehicle/profile/operating state, then measure
achieved cadence and response costs before making runtime claims.

## Examples and review

The [worked classification records](examples/polling-classifications.json)
include 28 commands from seven vehicle repositories, with source commit and
file hashes, command identity, observed intervals, and proposed categories.
A classification record is review metadata, not a valid signalset to load into
a client. The [review notes](polling-review.md) explain source provenance,
important boundary examples, and decisions to settle before adoption.
