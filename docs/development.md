# Development scope

_Independent educational implementation · 2026-11-06_

## Deliverable

A small Python 3.11+ package with no runtime dependencies. It demonstrates an
end-to-end mobile robot loop: grid planning, path following, command arbitration,
stop protection, chassis conversion, framed communication, and trajectory replay.
All code, maps and artwork are newly authored. No legacy source, team assets,
training data, weights, device protocol or private configuration is imported.

## Structure and choices

One repository keeps the working demonstration discoverable; focused modules
remain independently importable. Python makes the algorithms inspectable on
Windows and Linux without a ROS installation. ROS and vendor-specific drivers
remain future adapters, not implied existing support.

Coordinates use metres, radians and seconds. Positive x is forward, positive y
is left, positive yaw is counterclockwise. Commands carry linear speed and yaw
rate; Ackermann conversion produces steering angle. Timestamps share a caller
supplied monotonic clock.

## Implementation plan

- [x] Define immutable messages, validation and grid geometry; test malformed inputs.
- [x] Implement obstacle-inflated A*, no corner cutting, and pure pursuit.
- [x] Implement explicit mission transitions, command selection and latched e-stop.
- [x] Implement chassis conversion and bounded CRC-framed stream decoding.
- [x] Compose a deterministic simulator and export SVG, JSON and HTML replay.
- [x] Write a Chinese main README, English introduction, architecture and hardware guides.
- [x] Run tests, documented demos, packaging and local documentation checks.

## Acceptance

The normal demo must reach the goal without intersecting inflated map obstacles.
Emergency-stop and stale-input demos must end stationary. Commands from paused,
completed or faulted missions must remain zero. Fragmented, concatenated and
corrupted frames must decode predictably. The README must state that these are
software-only checks, not physical braking or real-vehicle validation.

## Review focus

Non-finite values; future/stale clocks; map corner crossing; empty scans; resumed
missions and stale remote commands; oversize/corrupt frames; steering saturation;
unreachable goals; simulation exits and generated local links.
