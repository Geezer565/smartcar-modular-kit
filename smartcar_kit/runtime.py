"""One command outlet composing mission, tracking, arbitration and safety."""

from dataclasses import dataclass

from .commands import CommandMux
from .control import PurePursuit, PursuitConfig
from .messages import Pose2D, LaserScan, Velocity, finite
from .mission import Mission, Event
from .safety import SafetyGate, SafetyConfig, SafetyResult


@dataclass(frozen=True)
class RuntimeOutput:
    result: SafetyResult
    state: str
    source: str
    target: tuple[float, float]


class RobotRuntime:
    def __init__(self, path, pursuit=None, safety=None):
        self.mission = Mission()
        self.follower = PurePursuit(path, pursuit or PursuitConfig())
        self.safety = SafetyGate(safety or SafetyConfig())
        self.commands = CommandMux(self.safety.config.command_timeout)

    def event(self, event: Event):
        self.mission.apply(event)
        if event in (Event.PAUSE, Event.FAIL, Event.RESET, Event.ARRIVE):
            self.commands.clear()
        if event == Event.RESET:
            self.follower = PurePursuit(list(self.follower.path), self.follower.config)

    def emergency_stop(self):
        self.safety.emergency_stop()
        self.event(Event.FAIL)

    def manual(self, command: Velocity, now: float):
        if not self.mission.can_move:
            raise ValueError('manual control requires a running mission')
        self.commands.submit('manual', command, now)

    def step(self, pose: Pose2D, *, pose_stamp: float, scan: LaserScan,
             now: float, dt: float) -> RuntimeOutput:
        finite(now, pose_stamp, dt)
        if not 0 < dt <= 0.5:
            raise ValueError('dt must be in (0, 0.5] seconds')
        pose_fresh = 0 <= now - pose_stamp <= self.safety.config.pose_timeout
        if self.mission.can_move and pose_fresh:
            automatic = self.follower.step(pose)
            if self.follower.finished:
                self.event(Event.ARRIVE)
            else:
                self.commands.submit('auto', automatic, now)
        entry = self.commands.select_entry(now)
        blocked = (self.follower.blocked_reason if
                   pose_fresh and entry.source == 'auto' and self.mission.can_move else None)
        if blocked:
            self.event(Event.PAUSE)
        result = self.safety.filter(
            entry.command, now=now, command_stamp=entry.stamp,
            pose_stamp=pose_stamp, scan=scan,
            enabled=self.mission.can_move, dt=dt,
        )
        if blocked and result.reason == 'disabled':
            result = SafetyResult(result.command, blocked)
        return RuntimeOutput(result, self.mission.state.value, entry.source, self.follower.target)
