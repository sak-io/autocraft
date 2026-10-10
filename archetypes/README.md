# Archetypes

An **archetype** is a project-type profile. The agents are the same for every project; the archetype tells them *what good looks like for this kind of product* — which questions to ask, what the architecture must cover, how to test, what to scan for, and what to check before release.

| Archetype | Build this when… | Biggest risk it guards against |
|---|---|---|
| [api-service](api-service/archetype.md) | other programs call you over a network | broken authorization, double-processing, breaking consumers |
| [web-app](web-app/archetype.md) | users work in a browser | inaccessible/insecure UI, missing states, flaky E2E |
| [mobile-app](mobile-app/archetype.md) | users install it from an app store | unrecoverable releases, offline failures, stranded old versions |
| [scheduled-job](scheduled-job/archetype.md) | it runs unattended on a schedule or queue | silent failure, duplicates, overlapping runs |
| [library-cli](library-cli/archetype.md) | developers install it or run it in a terminal | accidental breaking changes, supply-chain risk |

## Combining archetypes
Real products are usually several components, e.g. **mobile-app + api-service** or **web-app + api-service + scheduled-job**. List them all in `.autocraft/config.yml`:

```yaml
archetypes: [mobile-app, api-service]
```
Agents then read every listed profile. Rules for multi-component projects:
- One spec, one architecture doc, with a **section per component** and an explicit **contract** between them (usually the API's OpenAPI file).
- Work-breakdown tasks are tagged `[mobile]`, `[api]`, … and the contract-producing task comes first so components can progress in parallel.
- Components can live in one repo (monorepo: `apps/mobile`, `services/api`) — the default — or separate repos (run onboarding per repo).
- Release gates combine: e.g. an API change that mobile depends on must stay compatible with old app versions.

## How agents use them
Installed to `.autocraft/archetypes/<name>.md`. `/start` asks what you are building and records it in the config. The requirements-analyst uses the *Questions*, the architect the *Architecture must cover*, developers and reviewers the *Testing strategy* and *Common pitfalls*, the onboarder the *CI & tooling*, the security-auditor the *Security focus*, and the release-gatekeeper the *Release checklist additions*.

## Add your own
Copy any archetype file to `archetypes/<new-name>/archetype.md`, keep the same headings (`scripts/validate.sh` checks them), and fill them in. Ideas: `data-pipeline`, `ml-service`, `browser-extension`, `desktop-app`, `game`, `infrastructure-as-code`, `chatbot/agent`.
