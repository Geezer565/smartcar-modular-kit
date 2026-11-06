import math
import unittest

from smartcar_kit.messages import LaserScan, Pose2D, Velocity
from smartcar_kit.mission import Event
from smartcar_kit.runtime import RobotRuntime
from smartcar_kit.simulation import simulate


class RuntimeTests(unittest.TestCase):
    def test_stale_goal_pose_does_not_complete_or_advance_path(self):
        robot = RobotRuntime([(0, 0), (1, 0), (2, 0)])
        robot.event(Event.ARM)
        robot.event(Event.START)
        output = robot.step(Pose2D(2, 0, 0), pose_stamp=0,
                            scan=LaserScan((3,), 0, .1, 1), now=1, dt=.05)
        self.assertEqual(output.result.reason, 'stale_pose')
        self.assertEqual(output.state, 'running')
        self.assertFalse(robot.follower.finished)
        self.assertEqual(robot.follower.index, 0)
        recovered = robot.step(Pose2D(0, 0, 0), pose_stamp=1.1,
                               scan=LaserScan((3,), 0, .1, 1.1), now=1.1, dt=.05)
        self.assertGreater(recovered.result.command.speed, 0)

    def test_manual_overshoot_pauses_on_return_to_auto(self):
        robot = RobotRuntime([(0, 0), (1, 0)])
        robot.event(Event.ARM)
        robot.event(Event.START)
        robot.manual(Velocity(.1, 0), 1)
        scan = LaserScan((3,) * 36, -math.pi, 2 * math.pi / 36, 1)
        manual = robot.step(Pose2D(1.4, 0, 0), pose_stamp=1,
                            scan=scan, now=1, dt=.05)
        self.assertEqual(manual.source, 'manual')
        stopped = robot.step(Pose2D(1.4, 0, 0), pose_stamp=1.4,
                             scan=LaserScan(scan.ranges, scan.angle_min, scan.angle_increment, 1.4),
                             now=1.4, dt=.05)
        self.assertEqual(stopped.result.command, Velocity())
        self.assertEqual(stopped.result.reason, 'target_behind')
        self.assertEqual(stopped.state, 'paused')

    def test_pause_discards_manual_command(self):
        robot = RobotRuntime([(0, 0), (5, 0)])
        robot.event(Event.ARM)
        robot.event(Event.START)
        robot.manual(Velocity(.1, .5), 1.0)
        robot.event(Event.PAUSE)
        robot.event(Event.RESUME)
        output = robot.step(Pose2D(0, 0, 0), pose_stamp=1.0,
                            scan=LaserScan((3,), 0, .1, 1.0), now=1.0, dt=.05)
        self.assertEqual(output.source, 'auto')
        self.assertEqual(output.result.command.yaw_rate, 0)

    def test_reset_does_not_reset_emergency_latch(self):
        robot = RobotRuntime([(0, 0), (5, 0)])
        robot.emergency_stop()
        robot.event(Event.RESET)
        robot.event(Event.ARM)
        robot.event(Event.START)
        output = robot.step(Pose2D(0, 0, 0), pose_stamp=1,
                            scan=LaserScan((3,), 0, .1, 1), now=1, dt=.05)
        self.assertEqual(output.result.reason, 'estop')

    def test_normal_demo_and_fault_injections(self):
        for scenario in ('normal', 'estop', 'stale', 'obstacle'):
            with self.subTest(scenario=scenario):
                run = simulate(scenario)
                self.assertTrue(run['summary']['success'], run['summary'])
                self.assertFalse(run['summary']['collision'])
                self.assertEqual(run['summary']['final_speed'], 0)
                self.assertTrue(all(math.isfinite(row['speed']) for row in run['records']))
                if scenario == 'normal':
                    self.assertLessEqual(run['summary']['goal_error'], .12)
                    self.assertEqual(run['summary']['state'], 'completed')


if __name__ == '__main__':
    unittest.main()
