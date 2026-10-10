# Glossary (plain language)

| Term | Meaning |
|---|---|
| **Agent** | An AI assistant with a specific job description (e.g. reviewer) |
| **Skill / slash command** | A saved workflow you start by typing `/name` |
| **Repository (repo)** | The folder of your project's code and history, hosted on GitHub |
| **Branch** | A parallel copy of the code where changes are made safely |
| **`main`** | The branch holding the "official" version of the code |
| **Branch protection** | GitHub rules that stop anyone changing `main` without review and passing checks |
| **Pull request (PR)** | A proposal to merge a branch into `main`, with room for discussion |
| **Merge** | Accepting a PR so its changes become part of `main` |
| **Review / approve** | Reading a PR and giving a verdict |
| **CI (continuous integration)** | Automated checks that run on every change |
| **Lint** | Automatic style/mistake checker for code |
| **Unit test** | Small automatic test of one piece of logic |
| **Integration test** | Test that checks pieces working together (e.g. API + database) |
| **Coverage** | How much of the code the tests run |
| **Architecture** | The plan for how the system's parts fit together |
| **ADR** | A short note recording a design decision and why it was made |
| **Threat model** | A list of ways the system could be attacked and how we defend |
| **API** | A defined way for programs to talk to each other |
| **SCA** | Scanning the libraries you depend on for known vulnerabilities |
| **SAST** | Scanning your own code for security mistakes without running it |
| **Secret** | A password/API key; must never be in code |
| **Dependency** | A library your code uses |
| **Migration** | A change to the database structure |
| **Rollback** | Undoing a release if it goes wrong |
| **Walking skeleton** | The tiniest end-to-end version (app starts, one endpoint, CI green) built first |
| **Idempotent** | Doing it twice has the same effect as once (important for payments/orders) |
| **Release-ready** | Reviewed, tested, checked — only the human merge remains |
| **Autonomy level** | How often agents pause to ask you |
