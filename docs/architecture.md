# Architecture and interfaces

_SmartCar Kit · newly authored software modules_

## 🧭 Boundaries

The core operates on small Python values, not ROS messages, camera frames or
device handles. Input adapters supply timestamped observations. The runtime
selects a command and checks it before an output adapter converts and sends it.

| Contract | Units and meaning |
| --- | --- |
| `Pose2D(x, y, yaw)` | World position in metres; yaw in radians, CCW positive |
| `Velocity(speed, yaw_rate)` | Forward speed in m/s; CCW yaw rate in rad/s |
| `LaserScan(ranges, angle_min, angle_increment, stamp)` | Ranges in metres; angles in robot frame; +x forward, +y left |
| `TimedCommand(command, stamp, source)` | Time in seconds on the same monotonic clock as `now` |
| `RuntimeOutput` | Protected command, mission state, source and tracking target |

Range values: positive finite distances are hits; `+inf` means no return; NaN,
zero and negative values are invalid. The simulator returns a finite 3 m maximum.
No sensor-frame transform is done automatically. Clock values cannot be mixed
between different processes or hardware clocks without synchronization.

## 🏗️ A control cycle

1. `PurePursuit.step(pose)` proposes a forward velocity from the current path.
2. `CommandMux` chooses fresh manual control before fresh automatic control.
3. `Mission.can_move` allows motion only in the running state.
4. `SafetyGate.filter()` checks emergency stop, freshness, scan validity and obstacle distance.
5. Healthy commands receive velocity and rate limits. Stop conditions immediately produce zero.
6. The caller sends only `output.result.command` to its simulator or hardware adapter.

`RobotRuntime` composes these rules. No module starts shell commands or launches
other processes. Each instance owns its state; the library does not create
background threads or require a global message bus.

### Replacement points

| Change | Keep | Replace / add |
| --- | --- | --- |
| New planner | World coordinate path format | Produce `list[(x, y)]` |
| New controller | `Velocity` and the safety gate | Controller's candidate-generation method |
| New chassis | Protected `Velocity` | Output adapter and kinematic conversion |
| ROS 2 integration | Core modules | Translate messages and timestamps in an adapter |
| Camera / neural model | Core output contracts | Perception adapter with calibrated coordinates and freshness |

Image pixels are not world metres. A learned pixel target cannot be passed to
this world-frame path follower without a calibrated geometric conversion or a
different controller. No such conversion/model is included in this release.

## 🔄 Mission transitions

The table below is the actual `Mission.TRANSITIONS` contract. Unsupported events
raise `ValueError` instead of being silently accepted.

| From | Event | To |
| --- | --- | --- |
| Idle | Arm | Ready |
| Ready | Start | Running |
| Running | Pause | Paused |
| Paused | Resume | Running |
| Running | Arrive | Completed |
| Any state | Fail | Fault |
| Ready / Paused / Completed / Fault | Reset | Idle |

Pause, fail, reset and arrival clear buffered commands. Reset also resets the
path follower. Reset does not clear the separate emergency-stop latch. To recover
from an emergency stop, acknowledge clearing it, reset the mission, then arm and
start again. A normal obstacle or expired observation stops the output but does
not itself change the mission state; once observations are healthy, automatic
motion may resume. Applications requiring operator approval after every stop
should also apply `Event.PAUSE` when they receive a stop reason.

## 🛑 Protection behavior

| Reason | Condition | Output |
| --- | --- | --- |
| `estop` | Emergency latch set | Zero immediately |
| `disabled` | Mission is not running | Zero immediately |
| `stale_command` | Command too old or from the future | Zero immediately |
| `stale_pose` | Pose too old or from the future | Zero immediately |
| `stale_scan` | Scan too old or from the future | Zero immediately |
| `invalid_scan` | No monitored rays, NaN or non-positive monitored ray | Zero immediately |
| `obstacle` | Monitored obstacle inside configured stopping envelope | Zero immediately |
| `target_behind` | Automatic tracking target is behind the forward-only controller | Zero; runtime pauses mission |
| `ok` | Checks passed | Limited candidate command |

For translation the gate monitors a forward or rear angular sector. A reversal
also checks the previous direction while slowing down. In-place rotation checks
all supplied rays. These are simple directional checks, not swept-volume or
dynamic obstacle avoidance. They do not enforce a minimum angular scan coverage.
Provide sufficiently dense, calibrated scans covering the required directions.

The stopping envelope is:

```text
base stop distance + speed × command timeout + speed² / (2 × configured deceleration)
```

`speed` is the larger magnitude of the requested and previously permitted
commands. It is not a measured wheel speed. The formula is an educational guard,
not a calibrated physical brake model. Stopping bypasses the acceleration limiter;
a zero software command does not imply an instant physical stop.

## 🗺️ Planning and tracking assumptions

The grid origin is the lower-left map corner. A cell's world coordinate is its
centre. Occupied cells and map borders are inflated conservatively by
`ceil(radius / resolution)` cells in a square neighborhood. A* uses an
eight-connected grid, Euclidean edge costs and a Euclidean heuristic. Diagonal
steps cannot squeeze between two adjacent blocked cells.

The current path follower is forward-only and advances monotonically through
the nearest path index. It is intended for non-self-intersecting paths, a
reasonable initial heading, and low speeds. It does not support reversing,
relocalization after a large pose jump, self-intersections or dynamic replanning.
A* does not impose a minimum turning radius. Ackermann conversion can saturate
the steering angle; it does not make an infeasible path feasible.

The runtime does not update path progress or arrival using a stale/future pose.
If automatic tracking finds its target behind the vehicle, it pauses with
`target_behind`. Reposition or reorient the vehicle and explicitly resume, or
reset and supply a suitable new path. Fresh manual control remains available
while the mission is running, before this automatic handover check applies.

## 📦 Public interfaces

| Module | Entry points |
| --- | --- |
| `planning` | `GridMap(...)`, `.inflate(radius)`, `.world(cell)`, `astar(grid, start, goal)` |
| `control` | `PursuitConfig(...)`, `PurePursuit(path, config).step(pose)` |
| `mission` | `Mission().apply(Event)`, `.can_move`, `.history` |
| `commands` | `CommandMux(timeout).submit(source, command, stamp)`, `.select_entry(now)`, `.clear()` |
| `safety` | `SafetyGate(config).filter(...)`, `.emergency_stop()`, `.reset_emergency(acknowledged=True)` |
| `chassis` | `DifferentialDrive.to_wheels()`, `.from_wheels()`, `Ackermann.convert()` |
| `protocol` | `encode(frame)`, `StreamDecoder.feed(chunk)`, `velocity_frame()`, `read_velocity()` |
| `runtime` | `RobotRuntime(path).event()`, `.manual()`, `.step()`, `.emergency_stop()` |

See [the executable example](../examples/control_loop.py) and
[the tests](../tests/test_core.py) for concrete use.
