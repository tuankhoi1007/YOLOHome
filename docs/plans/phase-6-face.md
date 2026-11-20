# Phase 6 — Face recognition that opens the door

Requested 2026-11-20 by the owner: build the instructor-approved webcam face feature end to end, compare at least two approaches with a real evaluation report, and integrate the servo. The team has no face images yet. Effort: `max` for the study (two models, split, open-set metrics), `high` for the serial contract and dashboard. The owner asked for the implementation in the same session, so 6.1–6.3 were built together. Only 6.1 is ticked: D7 is settled and the dataset plan exists. 6.2 stays open until real photos replace `docs/face/smoke`. 6.3 stays open until a servo moves on the board.

## Plan

- Approaches, both on the laptop CPU, both pip wheels, no dlib and no CUDA: (A) OpenCV LBPH on a 100×100 grey crop; (B) YuNet detector + SFace 128-d embedding, score = max cosine against that person's gallery. OpenCV's published cosine hint is 0.363; the sweep may pick another point.
- Capture 40 aligned 112×112 shots per person into `code/data/faces/<Name>/`, plus `unknown/` for impostors. Gitignore the images. Names come from the CLI. One person is allowed, with a warning; the report needs at least two images each and a stratified 70/30 split, seed 42.
- Door rule: minimise false accept, then misidentification, then false reject. Ties take the stricter threshold. No new Adafruit feed. Pin configurable, default P4, never P0 or P14. Angles stay on the board (0 closed, 90 open). Auto-close is a gateway timer, default 10 s. The UI button still opens the door when recognition fails.
- An attempt is three stable frames, not every frame. Log who, score, threshold, accepted/rejected, timestamp to the existing web log and to a local jsonl file.
- Smoke test on painted patterns is allowed only if `synthetic: true` and it does not write `chosen.json`.

## Outcome

- Added capture, train/eval, runtime, door command, gateway integration, dashboard face/door status, and tests that use fake frames and a fake serial port. `python3 -m unittest discover -s code/tests -t code` passed (77 tests) after the change. `yolobit.py` was syntax-checked and not executed.
- D7 closed: LBPH vs YuNet+SFace, CPU, threshold rule above. D4 stays open; `SERVO_PIN` defaults to P4 (OhStem's servo example) and can be changed without a protocol bump other than the pin name in `DOOR:PIN`.
- Feeds unchanged: 7 of 10. Points/min unchanged. Protocol is v0.1.2.
- The committed numbers in `docs/face/smoke/` are a synthetic smoke test (painted textures, four fake people, 32/16/10). Both models have closed-set accuracy 1.0. At the security threshold LBPH FAR=0 FRR=0.9375 and SFace FAR=0 FRR=1, so LBPH wins on this texture set only. That is not a prediction for real faces. `chosen.json` was not written.
- Not hardware-verified: no webcam capture, no servo, no COM port, no Adafruit. The owner still has to flash `yolobit.py`, put the servo on the chosen pin, capture the five members plus unknowns, run `face_train.py`, set `FACE_ENABLE=1`, and confirm the door opens and the manual button still works when the face is rejected.
- Left open: real accuracy (6.2), hardware door (6.3), Gate 6, D4 pin, photo spoofing (no liveness), and D5 for a durable log (today: RAM plus `code/data/runtime/face_log.jsonl`).
