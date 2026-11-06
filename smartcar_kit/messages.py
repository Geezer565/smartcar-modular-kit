"""Shared units: metres, seconds, radians; x forward, y left, yaw CCW."""

from dataclasses import dataclass
import math


def finite(*values: float) -> None:
    if not all(isinstance(v, (float, int)) and not isinstance(v, bool)
               and math.isfinite(v) for v in values):
        raise ValueError('expected finite real numbers')


def positive(*values: float) -> None:
    finite(*values)
    if any(v <= 0 for v in values):
        raise ValueError('expected positive values')


def wrap_angle(angle: float) -> float:
    finite(angle)
    return (angle + math.pi) % (2 * math.pi) - math.pi


@dataclass(frozen=True)
class Pose2D:
    x: float
    y: float
    yaw: float

    def __post_init__(self):
        finite(self.x, self.y, self.yaw)


@dataclass(frozen=True)
class Velocity:
    speed: float = 0.0
    yaw_rate: float = 0.0

    def __post_init__(self):
        finite(self.speed, self.yaw_rate)


@dataclass(frozen=True)
class LaserScan:
    ranges: tuple[float, ...]
    angle_min: float
    angle_increment: float
    stamp: float

    def __post_init__(self):
        finite(self.angle_min, self.angle_increment, self.stamp)
        positive(self.angle_increment)
        object.__setattr__(self, 'ranges', tuple(self.ranges))


@dataclass(frozen=True)
class TimedCommand:
    command: Velocity
    stamp: float
    source: str

    def __post_init__(self):
        finite(self.stamp)
