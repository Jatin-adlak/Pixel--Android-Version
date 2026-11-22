# Recognition verification boundary

`backend/tests/test_face_search.py` tests event/result isolation, source changes, consent, duplicate jobs, progress, cached-index reuse, cancellation, expiry, query-file cleanup, similarity math, actual no-face rejection and the camera's MPO primary-frame decoder. These are workflow/contract tests, not an accuracy score.

`face_recognition/evaluate.py` measures a consented labeled-pair dataset. No held-out college-photo accuracy report has been produced yet. Multiple-selfie-face and low-quality handling are implemented but still need real-device example validation.

Evaluate with approximately 200 consenting participants, separating calibration and held-out evaluation photographs/sessions. Measure photo-level precision, recall, false-positive and false-negative rates, abstentions, and latency. Include no-match queries and varied lighting, pose, and group photographs. Avoid tuning and reporting final accuracy on the same samples.

Backend integration tests must verify event/model/version isolation, duplicate-photo removal, withdrawal/deletion during jobs, and absence of retained selfie files or sensitive logs. All reported metrics must come from actual consented runs.
