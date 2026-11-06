"""Forward-only geometric path tracking, with no image/model dependency."""

from dataclasses import dataclass
import math

from .messages import Pose2D, Velocity, finite, positive, wrap_angle


@dataclass(frozen=True)
class PursuitConfig:
    lookahead: float = 0.42
    cruise_speed: float = 0.45
    max_yaw_rate: float = 1.5
    goal_tolerance: float = 0.12
    slowdown_distance: float = 0.7

    def __post_init__(self):
        positive(self.lookahead, self.cruise_speed, self.max_yaw_rate,
                 self.goal_tolerance, self.slowdown_distance)


class PurePursuit:
    def __init__(self, path: list[tuple[float, float]], config: PursuitConfig):
        if not path:
            raise ValueError('path must not be empty')
        for point in path:
            if len(point) != 2:
                raise ValueError('path points must contain x and y')
            finite(*point)
        self.path = tuple(tuple(p) for p in path)
        self.config = config
        self.index = 0
        self.finished = False
        self.target = self.path[0]
        self.blocked_reason: str | None = None

    def step(self, pose: Pose2D) -> Velocity:
        cfg = self.config
        self.blocked_reason = None
        distance_to_goal = math.dist((pose.x, pose.y), self.path[-1])
        if self.finished or distance_to_goal <= cfg.goal_tolerance:
            self.finished = True
            return Velocity()
        # Monotone nearest point is suitable for non-self-intersecting A* paths.
        self.index = min(range(self.index, len(self.path)),
                         key=lambda i: math.dist((pose.x, pose.y), self.path[i]))
        target_index = self.index
        travelled = 0.0
        while target_index < len(self.path) - 1 and travelled < cfg.lookahead:
            travelled += math.dist(self.path[target_index], self.path[target_index + 1])
            target_index += 1
        self.target = self.path[target_index]
        dx, dy = self.target[0] - pose.x, self.target[1] - pose.y
        heading_error = wrap_angle(math.atan2(dy, dx) - pose.yaw)
        if abs(heading_error) >= math.pi / 2:
            self.blocked_reason = 'target_behind'
            return Velocity()
        speed = cfg.cruise_speed * min(1.0, distance_to_goal / cfg.slowdown_distance)
        speed *= max(0.15, math.cos(heading_error))
        curvature = 2 * math.sin(heading_error) / max(math.hypot(dx, dy), 1e-6)
        yaw_rate = max(-cfg.max_yaw_rate, min(cfg.max_yaw_rate, speed * curvature))
        return Velocity(speed, yaw_rate)
