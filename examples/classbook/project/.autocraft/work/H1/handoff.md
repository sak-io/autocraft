# H1 handoff
Branch fix/H1-qa-and-security. Suite: 539 passed, 0 failed, 0 xfail (was 6 xfail-strict). Bandit: 4 issues before and after (no new).
Commits: QA fixes D-1..D-9; security M-2/L-3/L-5/L-7 (+tests/test_h1_security.py); docs+handoff.
- D-1/D-2: web/deps.py class_id_param/booking_id_param (digits only, <=2**63-1, else 404 page); used by all {class_id}/{booking_id} routes.
- D-3: /health accepts HEAD. D-4: dummy_hash() warmed in create_app (the test calls create_app, not a lifespan).
- D-5: middleware.bare_page (viewport + stylesheet) used for 403/413/503; 500 page in logging_setup likewise.
- D-6: overflow-wrap: anywhere on body. D-7: admin list shows failed attempts via auth.service.last_sign_in.
- D-8: owner decision; test now asserts no "spots left" on greyed rows (code already complied).
- D-9: error handler looks up the signed-in user when no guard ran.
- M-2: signup records an attempt only while not throttled. L-3: purge_expired also deletes user_actions >1 day, messages >90 days (retention choice, adjust if wanted).
- L-5: CSP + form-action/base-uri/frame-ancestors; HSTS includeSubDomains (tests/test_web_shell.py updated to import CSP). L-7: os.umask(0o077) in create_app.
- NFR row "Token efficiency" added to docs/specs/classbook.md section 5 (no docs/spec/ dir exists; specs/ used).
Not done: M-1, M-3, L-2, L-4, L-6 (T8). Not pushed.
