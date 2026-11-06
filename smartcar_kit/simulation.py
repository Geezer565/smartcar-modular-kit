"""Deterministic unicycle simulation with grid ray casting and collision checks."""

from dataclasses import asdict, dataclass
import math
from pathlib import Path
import tomllib

from .control import PursuitConfig
from .messages import LaserScan, Pose2D, Velocity, positive, wrap_angle
from .mission import Event, State
from .planning import GridMap, astar
from .runtime import RobotRuntime
from .safety import SafetyConfig


@dataclass(frozen=True)
class DemoConfig:
    resolution: float = 0.2
    robot_radius: float = 0.16
    planning_clearance: float = 0.4
    dt: float = 0.05
    max_steps: int = 2500
    speed: float = 0.45
    lookahead: float = 0.42

    def __post_init__(self):
        positive(self.resolution, self.robot_radius, self.planning_clearance,
                 self.dt, self.speed, self.lookahead)
        if self.planning_clearance < self.robot_radius:
            raise ValueError('planning clearance must cover the robot radius')
        if self.dt > 0.5 or type(self.max_steps) is not int or self.max_steps <= 0:
            raise ValueError('invalid time step or step count')

    @classmethod
    def load(cls, path: Path | None):
        if path is None:
            return cls()
        with path.open('rb') as source:
            return cls(**tomllib.load(source)['simulation'])


def demo_world(config: DemoConfig) -> tuple[GridMap, tuple[int, int], tuple[int, int]]:
    obstacles = {(24, y) for y in range(23)}
    obstacles.update((40, y) for y in range(18, 40))
    return GridMap(60, 40, config.resolution, frozenset(obstacles)), (5, 8), (54, 30)


def move(pose: Pose2D, command: Velocity, dt: float) -> Pose2D:
    positive(dt)
    if abs(command.yaw_rate) < 1e-9:
        x = pose.x + command.speed * math.cos(pose.yaw) * dt
        y = pose.y + command.speed * math.sin(pose.yaw) * dt
    else:
        next_yaw = pose.yaw + command.yaw_rate * dt
        radius = command.speed / command.yaw_rate
        x = pose.x + radius * (math.sin(next_yaw) - math.sin(pose.yaw))
        y = pose.y - radius * (math.cos(next_yaw) - math.cos(pose.yaw))
    return Pose2D(x, y, wrap_angle(pose.yaw + command.yaw_rate * dt))


def collision(grid: GridMap, pose: Pose2D, radius: float) -> bool:
    r = grid.resolution
    if min(pose.x, pose.y, grid.width * r - pose.x, grid.height * r - pose.y) <= radius:
        return True
    for x, y in grid.blocked:
        nearest_x = max(x * r, min((x + 1) * r, pose.x))
        nearest_y = max(y * r, min((y + 1) * r, pose.y))
        if math.hypot(pose.x - nearest_x, pose.y - nearest_y) <= radius:
            return True
    return False


def scan_world(grid: GridMap, pose: Pose2D, now: float, count: int = 36) -> LaserScan:
    ranges = []
    # Ray samples at 1/4 cell spacing; this is a synthetic sensor, not a LiDAR driver.
    step = grid.resolution / 4
    for i in range(count):
        angle = pose.yaw - math.pi + i * 2 * math.pi / count
        dx, dy = math.cos(angle), math.sin(angle)
        distance = step
        while distance < 3.0:
            if not grid.free(grid.cell(pose.x + dx * distance, pose.y + dy * distance)):
                break
            distance += step
        ranges.append(min(distance, 3.0))
    return LaserScan(tuple(ranges), -math.pi, 2 * math.pi / count, now)


def simulate(scenario='normal', config=None) -> dict:
    if scenario not in ('normal', 'estop', 'stale', 'obstacle'):
        raise ValueError('unknown scenario')
    config = config or DemoConfig()
    grid, start, goal = demo_world(config)
    inflated = grid.inflate(config.planning_clearance)
    path = [grid.world(cell) for cell in astar(inflated, start, goal)]
    runtime = RobotRuntime(path, PursuitConfig(lookahead=config.lookahead, cruise_speed=config.speed),
                           SafetyConfig(stop_distance=config.robot_radius + 0.06))
    runtime.event(Event.ARM)
    runtime.event(Event.START)
    yaw = math.atan2(path[1][1] - path[0][1], path[1][0] - path[0][0])
    pose = Pose2D(*path[0], yaw)
    records = []
    hit = False
    injected_at = 3.0
    expected_reason = {'estop': 'estop', 'stale': 'stale_pose', 'obstacle': 'obstacle'}.get(scenario)
    for index in range(config.max_steps):
        now = round(index * config.dt, 9)
        scan = scan_world(grid, pose, now)
        pose_stamp = now
        if now >= injected_at:
            if scenario == 'estop' and not runtime.safety.estop:
                runtime.emergency_stop()
            elif scenario == 'stale':
                pose_stamp = now - 1.0
            elif scenario == 'obstacle':
                rays = list(scan.ranges)
                rays[len(rays) // 2] = config.robot_radius + 0.01
                scan = LaserScan(tuple(rays), scan.angle_min, scan.angle_increment, now)
        output = runtime.step(pose, pose_stamp=pose_stamp, scan=scan, now=now, dt=config.dt)
        command = output.result.command
        records.append(dict(t=now, x=pose.x, y=pose.y, yaw=pose.yaw,
                            speed=command.speed, yaw_rate=command.yaw_rate,
                            state=output.state, reason=output.result.reason,
                            source=output.source, target=list(output.target)))
        # Substeps check swept motion instead of checking only the endpoint.
        for substep in range(1, 6):
            predicted = move(pose, command, config.dt * substep / 5)
            if collision(grid, predicted, config.robot_radius):
                hit = True
                break
        if hit:
            break
        pose = move(pose, command, config.dt)
        if runtime.mission.state == State.COMPLETED:
            break
        if expected_reason and now >= injected_at + 0.5 and output.result.reason == expected_reason:
            break
    goal_error = math.dist((pose.x, pose.y), path[-1])
    success = (not hit and bool(records) and
               ((scenario == 'normal' and runtime.mission.state == State.COMPLETED)
                or (scenario != 'normal' and records[-1]['reason'] == expected_reason
                    and records[-1]['speed'] == records[-1]['yaw_rate'] == 0)))
    return dict(
        schema_version=1, scenario=scenario, config=asdict(config),
        world=dict(width=grid.width, height=grid.height, resolution=grid.resolution,
                   blocked=sorted(grid.blocked), inflated=sorted(inflated.blocked)),
        path=path, records=records, transitions=runtime.mission.history,
        summary=dict(success=success, collision=hit, state=runtime.mission.state.value,
                     reason=records[-1]['reason'], steps=len(records),
                     duration=records[-1]['t'], goal_error=goal_error,
                     distance=sum(math.dist((a['x'], a['y']), (b['x'], b['y']))
                                  for a, b in zip(records, records[1:])),
                     final_speed=records[-1]['speed']),
    )
