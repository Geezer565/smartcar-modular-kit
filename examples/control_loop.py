"""Run from the repository root: python -m examples.control_loop."""

from smartcar_kit.messages import Pose2D, LaserScan
from smartcar_kit.mission import Event
from smartcar_kit.runtime import RobotRuntime


def main():
    robot = RobotRuntime([(0, 0), (1, 0), (2, 0)])
    robot.event(Event.ARM)
    robot.event(Event.START)
    # Synthetic observations share one monotonic time base, in seconds.
    output = robot.step(
        Pose2D(0, 0, 0), pose_stamp=10.0,
        scan=LaserScan((2.0,) * 36, -3.141592653589793, 6.283185307179586 / 36, 10.0),
        now=10.0, dt=0.05,
    )
    print(output)
    # Output is printed only. No hardware transport is created.


if __name__ == '__main__':
    main()
