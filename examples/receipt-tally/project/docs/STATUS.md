# Receipt Tally status
- Spec (17 acceptance criteria, design, 3 tasks): done, owner defaults accepted.
- T1 core + T2 CLI/docs: built in one developer pass; review round 1: CHANGES-REQUESTED (2 MAJOR, 4 MINOR, 1 NIT); round 2 fixes applied (9 new red-then-green tests).
- Lead verification of round 2 (no third review, to save tokens): the reviewer's own probes re-run, surviving mutant (thousands separator) now killed, 36 tests pass, bandit clean.
- RELEASE-READY for the owner to use. Nothing to deploy: it is a local command.
- Known, accepted: skipped bad rows still exit 0 (they are listed); sum-precision test cannot distinguish the precision-60 context.
