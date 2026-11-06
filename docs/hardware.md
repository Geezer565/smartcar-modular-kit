# Connect your own vehicle

_Adapter guide · no vendor compatibility or real-car validation claimed_

## 🔌 What already exists

The toolkit contains software command generation, checking, kinematic conversion
and an example wire format. It contains no motor driver, serial-port I/O, firmware,
camera processing, LiDAR driver, SLAM or hardware clock synchronization.

| Part of your car | What you must supply | Value the core receives / produces |
| --- | --- | --- |
| Position source | Odometry / localization adapter | `Pose2D` plus its acquisition time |
| Range sensor | Driver and frame conversion | `LaserScan` in the robot frame |
| Camera | Optional perception logic and calibration | World path or a separate controller |
| Upper computer | Scheduling, observations and output adapter | Runs `RobotRuntime.step()` |
| Lower controller | Firmware, motor control and independent watchdog | Receives bounded commands |
| Chassis | Dimensions, wheel limits and steering limits | `DifferentialDrive` or `Ackermann` conversion |

## 📐 Coordinates and conversions

Use one convention end to end: metres, seconds, radians; robot x forward, y left,
yaw CCW. Convert encoder units, millimetres and degrees at the input/output edge.
Keep acquisition timestamps rather than stamping an old observation as newly
received. Use a shared monotonic time base or explicitly convert clocks.

### Differential chassis

```python
from smartcar_kit.chassis import DifferentialDrive
from smartcar_kit.messages import Velocity

drive = DifferentialDrive(track_width=0.32, wheel_radius=0.05)
left_rad_s, right_rad_s = drive.to_wheels(Velocity(0.2, 0.3))
```

Wheel outputs are rad/s, not PWM and not RPM. Motor direction, gearing, maximum
wheel speed and wheel-speed regulation belong in your lower-level adapter. If a
wheel limit is exceeded, scale both wheels together to preserve curvature.

### Ackermann chassis

```python
from smartcar_kit.chassis import Ackermann
from smartcar_kit.messages import Velocity

drive = Ackermann(wheelbase=0.25, max_steering=0.5)
speed, steering_rad = drive.convert(Velocity(0.2, 0.3))
```

An Ackermann chassis cannot turn in place. At near-zero speed the conversion
returns zero. Steering saturation changes the achievable yaw rate. The included
unicycle demo does not model that saturation, tyre slip or a servo's response.
Use a curvature-feasible planner and an appropriate vehicle model before claiming
Ackermann path-following performance.

## 📡 One command outlet

An adapter's loop should acquire observations, call `RobotRuntime.step()` and
transmit only the returned protected command. The transport should send a stop
when exiting and close resources in `finally`. Treat exceptions as reasons to
stop, not reasons to keep the previous speed indefinitely.

The upper-level safety gate cannot run if the program freezes or loses power.
The lower controller must independently stop when valid commands stop arriving.
The example wire format provides a sequence field and a checksum but no actuator
watchdog, authentication or encryption. Implement those at the appropriate layer;
see [protocol.md](protocol.md).

## 🧪 Practical bring-up order

1. With wheels lifted, verify command units, wheel directions and steering sign.
2. Verify the lower controller's timeout without relying on the upper program.
3. Check emergency stop, lost link, malformed frames and restart behavior.
4. Validate sensor frames, acquisition timestamps and missing-scan handling.
5. Run single low-speed commands in an empty controlled area.
6. Calibrate limits and stopping behavior before enabling path following.

Keep the software simulation results separate from your new hardware results.
Record chassis dimensions, controller version, sensor models, actual test limits
and what was measured. A successful message exchange alone is not a successful
vehicle-control test.
