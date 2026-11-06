"""Manual commands override autonomy only while fresh; stale commands expire."""

from .messages import TimedCommand, Velocity, finite, positive


class CommandMux:
    PRIORITY = {'auto': 10, 'manual': 20}

    def __init__(self, timeout: float = 0.3):
        positive(timeout)
        self.timeout = timeout
        self._entries: dict[str, TimedCommand] = {}

    def submit(self, source: str, command: Velocity, stamp: float) -> None:
        if source not in self.PRIORITY:
            raise ValueError('source must be auto or manual')
        finite(stamp)
        previous = self._entries.get(source)
        if previous and stamp < previous.stamp:
            raise ValueError('out-of-order command')
        self._entries[source] = TimedCommand(command, stamp, source)

    def select_entry(self, now: float) -> TimedCommand:
        finite(now)
        live = [item for item in self._entries.values()
                if 0 <= now - item.stamp <= self.timeout]
        if not live:
            return TimedCommand(Velocity(), now, 'none')
        return max(live, key=lambda item: self.PRIORITY[item.source])

    def select(self, now: float) -> Velocity:
        return self.select_entry(now).command

    def clear(self) -> None:
        """Call when pausing, changing mode or resetting a mission."""
        self._entries.clear()
