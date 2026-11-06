# Intent: <anomaly or incident, short title>
Author: <agent or person that raised it>. Status: draft | accepted | closed.

<!-- Maintain stage: an anomaly found in production (or a breached band, see templates/operate/bands.yaml) re-enters the lifecycle as an intent.
     Save as docs/intent/<name>.md; the owner or on-call triages it (fix now, schedule, dismiss). Dismissals tune the bands. -->

## Problem
<The anomaly, when it started, and the evidence: metric and band breached, log lines, the deploy or change it lines up with.>

## Proposed outcome
<What "back to normal" looks like, in numbers (for example: 5xx rate inside its band).>

## Affected users and systems
<Who feels it, which services, which release.>

## Constraints
<What the responder may and may not do: allowed routes (open a PR, run an approved runbook), no direct production access.>

## Open questions
<Cause not yet proven, whether a rollback is needed, who owns the fix.>

## Regression test
<The test or eval that will keep this class of incident from returning. Add it when the fix ships (see .autocraft/templates/evals).>
