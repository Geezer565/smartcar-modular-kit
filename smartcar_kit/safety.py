"""Software command checks; these do not replace a physical emergency stop."""

from dataclasses import dataclass
import math

from .messages import LaserScan, Velocity, finite, positive, wrap_angle


@dataclass(frozen=True)
class SafetyConfig:
    max_speed: float = 0.6
    max_yaw_rate: float = 1.8
    max_acceleration: float = 0.7
    max_yaw_acceleration: float = 3.0
    command_timeout: float = 0.3
    pose_timeout: float = 0.3
    scan_timeout: float = 0.3
    stop_distance: float = 0.22
    braking_deceleration: float = 0.8
    sector_half_angle: float = math.pi / 4

    def __post_init__(self):
        positive(*self.__dict__.values())
        if self.sector_half_angle > math.pi:
            raise ValueError('sector half angle cannot exceed pi')


@dataclass(frozen=True)
class SafetyResult:
    command: Velocity
    reason: str


class SafetyGate:
    def __init__(self, config: SafetyConfig):
        self.config = config
        self.estop = False
        self.previous = Velocity()

    def emergency_stop(self) -> None:
        self.estop = True
        self.previous = Velocity()

    def reset_emergency(self, *, acknowledged: bool) -> None:
        if acknowledged is not True:
            raise ValueError('explicit acknowledgement required')
        self.estop = False

    def _stop(self, reason: str) -> SafetyResult:
        self.previous = Velocity()
        return SafetyResult(Velocity(), reason)

    def filter(self, command: Velocity, *, now: float, command_stamp: float,
               pose_stamp: float, scan: LaserScan, enabled: bool, dt: float) -> SafetyResult:
        finite(now, command_stamp, pose_stamp, dt)
        if not 0 < dt <= 0.5:
            raise ValueError('dt must be in (0, 0.5] seconds')
        cfg = self.config
        if self.estop:
            return self._stop('estop')
        if not enabled:
            return self._stop('disabled')
        for label, stamp, timeout in (
            ('command', command_stamp, cfg.command_timeout),
            ('pose', pose_stamp, cfg.pose_timeout),
            ('scan', scan.stamp, cfg.scan_timeout),
        ):
            if not 0 <= now - stamp <= timeout:
                return self._stop('stale_' + label)
        monitored = []
        directions = []
        for speed in (command.speed, self.previous.speed):
            if speed > 0:
                directions.append(0.0)
            elif speed < 0:
                directions.append(math.pi)
        rotating = not directions and max(abs(command.yaw_rate), abs(self.previous.yaw_rate)) > 0
        for index, distance in enumerate(scan.ranges):
            angle = scan.angle_min + index * scan.angle_increment
            if rotating or not directions or any(
                abs(wrap_angle(angle - direction)) <= cfg.sector_half_angle
                for direction in directions
            ):
                # Positive infinity is a valid no-return ray; NaN/zero/negative are invalid.
                if math.isnan(distance) or distance <= 0:
                    return self._stop('invalid_scan')
                monitored.append(distance)
        if not monitored:
            return self._stop('invalid_scan')
        speed = max(abs(command.speed), abs(self.previous.speed))
        distance_needed = (cfg.stop_distance + speed * cfg.command_timeout
                           + speed * speed / (2 * cfg.braking_deceleration))
        if (directions or rotating) and min(monitored) <= distance_needed:
            return self._stop('obstacle')
        target_speed = max(-cfg.max_speed, min(cfg.max_speed, command.speed))
        target_yaw = max(-cfg.max_yaw_rate, min(cfg.max_yaw_rate, command.yaw_rate))
        def approach(previous, target, step):
            return previous + max(-step, min(step, target - previous))
        output = Velocity(
            approach(self.previous.speed, target_speed, cfg.max_acceleration * dt),
            approach(self.previous.yaw_rate, target_yaw, cfg.max_yaw_acceleration * dt),
        )
        self.previous = output
        return SafetyResult(output, 'ok')
