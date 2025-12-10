from dataclasses import dataclass, field
from datetime import datetime, time
from enum import Enum
from typing import List, Optional


class Priority(Enum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2


@dataclass
class Task:
    """Represents a user task to be scheduled."""
    id: str
    name: str
    subject: str
    estimated_hours: float
    deadline: datetime
    priority: Priority
    can_be_split: bool = True
    description: Optional[str] = None

    def __post_init__(self):
        if self.estimated_hours <= 0:
            raise ValueError("Estimated hours must be positive")

    @property
    def priority_weight(self) -> float:
        """Get weight multiplier based on priority."""
        weights = {Priority.LOW: 0.8, Priority.MEDIUM: 1.0, Priority.HIGH: 1.3}
        return weights[self.priority]

    @property
    def weighted_hours(self) -> float:
        """Calculate hours adjusted by priority."""
        return self.estimated_hours * self.priority_weight


@dataclass
class CalendarEvent:
    """Represents a calendar event."""
    title: str
    start: datetime
    end: datetime
    description: Optional[str] = None
    event_id: Optional[str] = None

    def __post_init__(self):
        if self.end <= self.start:
            raise ValueError("End time must be after start time")

    @property
    def duration_hours(self) -> float:
        """Get duration in hours."""
        return (self.end - self.start).total_seconds() / 3600

    def overlaps_with(self, other: 'CalendarEvent') -> bool:
        """Check if this event overlaps with another."""
        return (self.start < other.end) and (other.start < self.end)


@dataclass
class WorkingHours:
    """User's working/study hours."""
    start_end: List[tuple[time, time]]

    def __post_init__(self):
        for start, end in self.start_end:
            if end <= start:
                raise ValueError("Each start time must be before the corresponding end time")


@dataclass
class UserPreferences:
    """User's scheduling preferences and constraints."""
    working_hours: WorkingHours
    max_daily_hours: float
    buffer_minutes: int = 15

    def __post_init__(self):
        if self.max_daily_hours <= 0:
            raise ValueError("Max daily hours must be positive")


@dataclass
class Schedule:
    """Generated schedule containing calendar events."""
    events: List[CalendarEvent] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def total_hours(self) -> float:
        """Total scheduled hours."""
        return sum(event.duration_hours for event in self.events)

    @property
    def total_tasks(self) -> int:
        """Count unique tasks in schedule."""
        return len(set(event.title for event in self.events))

    def has_conflicts(self) -> bool:
        """Check if any events overlap."""
        for i, event1 in enumerate(self.events):
            for event2 in self.events[i+1:]:
                if event1.overlaps_with(event2):
                    return True
        return False