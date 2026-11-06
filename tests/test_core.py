import math
import unittest

from smartcar_kit.messages import Pose2D, Velocity, LaserScan
from smartcar_kit.planning import GridMap, astar
from smartcar_kit.control import PurePursuit, PursuitConfig
from smartcar_kit.mission import Mission, State, Event
from smartcar_kit.safety import SafetyGate, SafetyConfig
from smartcar_kit.commands import CommandMux
from smartcar_kit.chassis import Ackermann, DifferentialDrive
from smartcar_kit.protocol import Frame, StreamDecoder, encode, velocity_frame, read_velocity


class PlanningTests(unittest.TestCase):
    def test_path_avoids_wall(self):
        grid = GridMap(8, 8, 0.2, frozenset((3, y) for y in range(6)))
        path = astar(grid, (1, 1), (6, 1))
        self.assertEqual(path[0], (1, 1))
        self.assertEqual(path[-1], (6, 1))
        self.assertTrue(all(grid.free(p) for p in path))
        self.assertTrue(any(y >= 6 for _, y in path))

    def test_no_diagonal_corner_cut(self):
        grid = GridMap(2, 2, 1.0, frozenset({(0, 1), (1, 0)}))
        with self.assertRaises(ValueError):
            astar(grid, (0, 0), (1, 1))

    def test_inflation_and_boundary(self):
        grid = GridMap(10, 10, 0.1, frozenset({(5, 5)})).inflate(0.1)
        self.assertFalse(grid.free((5, 4)))
        self.assertFalse(grid.free((0, 5)))
        self.assertTrue(grid.free((3, 3)))

    def test_invalid_grid_and_blocked_start(self):
        with self.assertRaises(ValueError):
            GridMap(0, 2, 1.0)
        with self.assertRaises(ValueError):
            astar(GridMap(3, 3, 1, frozenset({(0, 0)})), (0, 0), (2, 2))


class ControlTests(unittest.TestCase):
    def test_straight_and_left(self):
        follower = PurePursuit([(0, 0), (2, 0)], PursuitConfig())
        self.assertAlmostEqual(follower.step(Pose2D(0, 0, 0)).yaw_rate, 0)
        follower = PurePursuit([(0, 0), (1, 1), (2, 1)], PursuitConfig())
        self.assertGreater(follower.step(Pose2D(0, 0, 0)).yaw_rate, 0)

    def test_goal_stops(self):
        follower = PurePursuit([(0, 0), (1, 0)], PursuitConfig())
        self.assertEqual(follower.step(Pose2D(1, 0, 0)), Velocity())
        self.assertTrue(follower.finished)

    def test_target_behind_stops_without_claiming_arrival(self):
        follower = PurePursuit([(0, 0), (1, 0)], PursuitConfig())
        self.assertEqual(follower.step(Pose2D(1.4, 0, 0)), Velocity())
        self.assertEqual(follower.blocked_reason, 'target_behind')
        self.assertFalse(follower.finished)

    def test_bad_path(self):
        with self.assertRaises(ValueError):
            PurePursuit([], PursuitConfig())
        with self.assertRaises(ValueError):
            PurePursuit([(0, 0), (math.nan, 1)], PursuitConfig())

    def test_chassis_roundtrip(self):
        drive = DifferentialDrive(track_width=0.4, wheel_radius=0.05)
        command = Velocity(0.3, -0.4)
        left, right = drive.to_wheels(command)
        restored = drive.from_wheels(left, right)
        self.assertAlmostEqual(command.speed, restored.speed)
        self.assertAlmostEqual(command.yaw_rate, restored.yaw_rate)

    def test_ackermann_limits(self):
        drive = Ackermann(wheelbase=0.25, max_steering=0.5)
        speed, steering = drive.convert(Velocity(0.2, 9))
        self.assertEqual(speed, 0.2)
        self.assertEqual(steering, 0.5)
        self.assertEqual(drive.convert(Velocity(0, 1)), (0, 0))

    def test_finite_messages(self):
        with self.assertRaises(ValueError):
            Velocity(math.nan, 0)
        with self.assertRaises(ValueError):
            Pose2D(0, 0, math.inf)


class MissionTests(unittest.TestCase):
    def test_transition_lifecycle(self):
        mission = Mission()
        mission.apply(Event.ARM)
        mission.apply(Event.START)
        mission.apply(Event.PAUSE)
        self.assertFalse(mission.can_move)
        mission.apply(Event.RESUME)
        self.assertTrue(mission.can_move)
        mission.apply(Event.ARRIVE)
        self.assertEqual(mission.state, State.COMPLETED)
        self.assertFalse(mission.can_move)

    def test_fault_requires_reset(self):
        mission = Mission()
        mission.apply(Event.FAIL)
        with self.assertRaises(ValueError):
            mission.apply(Event.START)
        mission.apply(Event.RESET)
        self.assertEqual(mission.state, State.IDLE)

    def test_mux_priorities_expiry_and_clock(self):
        mux = CommandMux(timeout=0.3)
        mux.submit('auto', Velocity(0.2, 0), 1.0)
        mux.submit('manual', Velocity(0.1, 0.2), 1.0)
        self.assertEqual(mux.select(1.1).speed, 0.1)
        self.assertEqual(mux.select(1.5), Velocity())
        self.assertEqual(mux.select(0.9), Velocity())
        mux.clear()
        self.assertEqual(mux.select(1.1), Velocity())


class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.gate = SafetyGate(SafetyConfig())

    def tick(self, **kwargs):
        params = dict(command=Velocity(0.4, 0.4), now=1.0, command_stamp=1.0,
                      pose_stamp=1.0, scan=LaserScan((2.0,), 0.0, 0.1, 1.0),
                      enabled=True, dt=0.1)
        params.update(kwargs)
        return self.gate.filter(**params)

    def test_disabled_and_stale_stop_immediately(self):
        self.tick()
        self.assertEqual(self.tick(enabled=False).command, Velocity())
        self.assertEqual(self.tick(pose_stamp=0).reason, 'stale_pose')
        self.assertEqual(self.tick(command_stamp=0).reason, 'stale_command')

    def test_front_obstacle_and_invalid_scan(self):
        self.assertEqual(self.tick(scan=LaserScan((0.1,), 0, 0.1, 1)).reason, 'obstacle')
        self.assertEqual(self.tick(scan=LaserScan((math.nan,), 0, 0.1, 1)).reason, 'invalid_scan')
        self.assertEqual(self.tick(scan=LaserScan((), 0, 0.1, 1)).reason, 'invalid_scan')

    def test_future_and_stale_scan(self):
        self.assertEqual(self.tick(pose_stamp=2).reason, 'stale_pose')
        self.assertEqual(self.tick(scan=LaserScan((2,), 0, .1, 0)).reason, 'stale_scan')

    def test_estop_latched_until_acknowledged(self):
        self.gate.emergency_stop()
        self.assertEqual(self.tick().reason, 'estop')
        with self.assertRaises(ValueError):
            self.gate.reset_emergency(acknowledged=False)
        self.gate.reset_emergency(acknowledged=True)
        self.assertEqual(self.tick().reason, 'ok')

    def test_acceleration_and_limits(self):
        result = self.tick()
        self.assertLessEqual(result.command.speed, self.gate.config.max_acceleration * .1)
        self.assertLessEqual(abs(result.command.yaw_rate), self.gate.config.max_yaw_rate)

    def test_reverse_checks_rear(self):
        scan = LaserScan((0.1, 3), 0, math.pi, 1)
        self.assertEqual(self.tick(command=Velocity(-.2, 0), scan=scan).reason, 'ok')
        scan = LaserScan((3, .1), 0, math.pi, 1)
        self.assertEqual(self.tick(command=Velocity(-.2, 0), scan=scan).reason, 'obstacle')

    def test_stopping_rotation_checks_remaining_motion(self):
        self.tick(command=Velocity(0, .6))
        self.assertGreater(self.gate.previous.yaw_rate, 0)
        result = self.tick(command=Velocity(), scan=LaserScan((.01,), 0, .1, 1))
        self.assertEqual(result.reason, 'obstacle')
        self.assertEqual(result.command, Velocity())


class ProtocolTests(unittest.TestCase):
    def test_golden_crc(self):
        import binascii
        self.assertEqual(binascii.crc_hqx(b'123456789', 0xffff), 0x29b1)

    def test_fragmented_and_concatenated_frames(self):
        frame = Frame(1, 7, b'abc')
        data = encode(frame)
        decoder = StreamDecoder()
        self.assertEqual(decoder.feed(data[:3]), [])
        self.assertEqual(decoder.feed(data[3:] + data), [frame, frame])

    def test_corruption_noise_and_oversized_header(self):
        good = encode(Frame(2, 8, b'ok'))
        bad = bytearray(good)
        bad[-1] ^= 1
        decoder = StreamDecoder()
        result = decoder.feed(b'noise\xa5' + bytes(bad) + b'\xa5\x5a\x01\x01\x00\x00\xff\xff' + good)
        self.assertEqual(result, [Frame(2, 8, b'ok')])

    def test_command_roundtrip_and_validation(self):
        command = Velocity(.23, -.7)
        frame = velocity_frame(command, 25)
        actual = read_velocity(StreamDecoder().feed(encode(frame))[0])
        self.assertAlmostEqual(actual.speed, command.speed, places=6)
        with self.assertRaises(ValueError):
            read_velocity(Frame(2, 0, frame.payload))
        with self.assertRaises(ValueError):
            encode(Frame(1, 0, b'x' * 513))


if __name__ == '__main__':
    unittest.main()
