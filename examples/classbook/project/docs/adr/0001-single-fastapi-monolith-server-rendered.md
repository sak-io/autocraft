# ADR 0001: One FastAPI app with server-rendered pages

- **Status:** Accepted  ·  **Date:** 2026-10-10

## Context
Small studio, <1,000 students, tiny budget, available tools are Python 3.13 + FastAPI + Jinja2. The archetype (fullstack-app) wants UI and server logic in one codebase.

## Decision
A single FastAPI process serves HTML pages (Jinja2 templates, plain forms) and holds all rules in a `services/` layer; no separate JavaScript front end, no API/worker split.

## Alternatives considered
1. React/Next.js front end + JSON API – two projects, two deployments, a build toolchain and more attack surface for ~6 pages; not justified.
2. FastAPI JSON API only – no UI for Maya and students; the UI is the product.

## Consequences
Cheapest to run and test (httpx TestClient covers whole flows). Pages are less "app-like"; acceptable. Rules live in services so a JSON API can be added later without rewriting them.
