"""Explicit mission transitions. State changes never launch shell processes."""

from enum import Enum


class State(str, Enum):
    IDLE = 'idle'
    READY = 'ready'
    RUNNING = 'running'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    FAULT = 'fault'


class Event(str, Enum):
    ARM = 'arm'
    START = 'start'
    PAUSE = 'pause'
    RESUME = 'resume'
    ARRIVE = 'arrive'
    FAIL = 'fail'
    RESET = 'reset'


class Mission:
    TRANSITIONS = {
        (State.IDLE, Event.ARM): State.READY,
        (State.READY, Event.START): State.RUNNING,
        (State.RUNNING, Event.PAUSE): State.PAUSED,
        (State.PAUSED, Event.RESUME): State.RUNNING,
        (State.RUNNING, Event.ARRIVE): State.COMPLETED,
        (State.COMPLETED, Event.RESET): State.IDLE,
        (State.FAULT, Event.RESET): State.IDLE,
        (State.PAUSED, Event.RESET): State.IDLE,
        (State.READY, Event.RESET): State.IDLE,
    }

    def __init__(self):
        self.state = State.IDLE
        self.history: list[tuple[str, str, str]] = []

    @property
    def can_move(self) -> bool:
        return self.state == State.RUNNING

    def apply(self, event: Event) -> State:
        event = Event(event)
        previous = self.state
        if event == Event.FAIL:
            self.state = State.FAULT
        else:
            try:
                self.state = self.TRANSITIONS[(self.state, event)]
            except KeyError:
                raise ValueError(f'event {event.value} is not allowed in {self.state.value}') from None
        self.history.append((previous.value, event.value, self.state.value))
        return self.state
