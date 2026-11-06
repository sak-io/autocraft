# Review rules for this repository

<!-- Read by pr-reviewer before every review. Owned by the tech lead; tune it monthly by rating past findings. -->

## Passes (run all, every PR)
1. **Bugs and logic errors**: edge cases, error paths, concurrency, resource leaks.
2. **Security**: injection, authn/authz gaps, secrets or PII in logs and errors.
3. **Compliance**: matches the spec, the task plan and the architecture; deviations are declared.

## Severity
- Reserve `[BLOCKER]`/`[MAJOR]` for findings that break behavior, leak data or breach a policy.
- Report at most five `[NIT]`s per review; summarise the rest as a count.

## Do not report
- Generated files and anything CI already enforces (formatting, lint).
