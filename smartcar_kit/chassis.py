"""Kinematic conversions, not vendor-specific device drivers."""

from dataclasses import dataclass
import math

from .messages import Velocity, finite, positive


@dataclass(frozen=True)
class DifferentialDrive:
    track_width: float = 0.32
    wheel_radius: float = 0.05

    def __post_init__(self):
        positive(self.track_width, self.wheel_radius)

    def to_wheels(self, command: Velocity) -> tuple[float, float]:
        """Return left/right wheel angular velocities, rad/s."""
        half = command.yaw_rate * self.track_width / 2
        return ((command.speed - half) / self.wheel_radius,
                (command.speed + half) / self.wheel_radius)

    def from_wheels(self, left: float, right: float) -> Velocity:
        finite(left, right)
        return Velocity((left + right) * self.wheel_radius / 2,
                        (right - left) * self.wheel_radius / self.track_width)


@dataclass(frozen=True)
class Ackermann:
    wheelbase: float = 0.25
    max_steering: float = 0.55

    def __post_init__(self):
        positive(self.wheelbase, self.max_steering)
        if self.max_steering >= math.pi / 2:
            raise ValueError('steering limit must be below pi/2')

    def convert(self, command: Velocity) -> tuple[float, float]:
        """Return speed (m/s), steering (rad). Cannot turn in place."""
        if abs(command.speed) < 1e-6:
            return 0.0, 0.0
        steering = math.atan(command.yaw_rate * self.wheelbase / command.speed)
        return command.speed, max(-self.max_steering, min(self.max_steering, steering))
