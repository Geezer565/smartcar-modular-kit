# Software validation record

_2026-11-06 · Windows · Python 3.13.15_

## 🧪 Reproduce

```bash
python -m unittest discover -s tests -v
python tools/check_repository.py
python -m smartcar_kit demo --config examples/demo.toml
python -m smartcar_kit demo --scenario obstacle --output outputs/obstacle
python -m smartcar_kit demo --scenario stale --output outputs/stale
python -m smartcar_kit demo --scenario estop --output outputs/estop
python -m smartcar_kit protocol-demo
python -m examples.control_loop
```

## 📊 Default scenario results

All 30 unit and integration tests passed. An independent code review identified
three additional edge cases; regression checks now cover remaining rotation
during a stop, stale arrival observations, and a manual-to-auto handover after
passing the destination. These fixes passed alongside the original scenarios.

These values are generated from the included synthetic scene using the default
configuration. They describe simulated time, not elapsed computation time.

| Scenario | Expected result | Observed final result | Simulated time | Collision |
| --- | --- | --- | ---: | --- |
| `normal` | Reach destination and stop | `completed`, speed 0 | 32.10 s | No |
| `obstacle` | Stop on an injected close forward ray | `obstacle`, speed 0 | 3.50 s | No |
| `stale` | Stop when pose time is old | `stale_pose`, speed 0 | 3.50 s | No |
| `estop` | Stop and hold the emergency latch | `fault` / `estop`, speed 0 | 3.50 s | No |

Normal scene: 643 records, approximately 13.470 m simulated travel, 0.1178 m final
position error against a 0.12 m goal tolerance. The report's `disabled` reason at
normal completion is expected: a completed mission no longer enables motion.

Faults are injected at 3.0 s and held for another 0.5 s to observe stationary
commands. The obstacle scenario injects one scan ray; it does not model a moving
physical object. Each scenario's `success` field is checked against its own
expected result.

## 📡 Communication check

The documented in-memory example produces this frame for 0.3 m/s, -0.2 rad/s,
sequence 1:

```text
a5 5a 01 01 01 00 08 00 9a 99 99 3e cd cc 4c be 51 aa
```

The decoder reconstructs it from two fragments. Unit checks cover CRC reference
value, concatenated frames, corruption, noise, invalid headers and wrong payloads.
No physical serial or network link is part of this check.

## 🎬 Presentation check

The default replay was opened in a separate headless Chrome instance and visually
inspected at 1280 × 960. The map, path, vehicle marker, recorded values, time slider
and playback controls rendered. Program-generated SVG files are also parsed as
XML; relative documentation links are checked locally. Remote badges are decorative
labels, not evidence of an online build.

The optional `tools/check_replay.py` browser check exercised seek-to-end, play,
restart and pause against the generated page; all four passed. It requires an
installed Chromium-family browser, but is not needed to run the toolkit itself.

## 📦 Installation check

The project was built as `smartcar_modular_kit-0.1.0-py3-none-any.whl`, installed
into a separate temporary directory without runtime dependencies, then run from
that directory. Both the protocol example and normal simulation passed. Build
tools were downloaded in an isolated build environment; this did not change an
existing training environment.

## 📍 Evidence limits

- Unit checks and the four synthetic scenarios validate this implementation's software behavior
- Simulated pose is ideal; ranges are generated from an occupancy grid
- Collision checks use a circular robot and five substeps per control step
- Dynamics have no acceleration lag, slip, actuator latency or braking delay
- No physical vehicle, radar, camera, lower-controller firmware or ROS integration was tested
- No learned model training or real dataset is included
- Ubuntu and Python 3.11 are targets in the workflow, not locally observed test environments

Add separate hardware evidence if adapters are implemented later. Do not replace
these limitations with claims of real-world vehicle performance.
