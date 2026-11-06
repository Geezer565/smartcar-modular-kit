"""Eight-connected A* on a conservative occupancy grid."""

from dataclasses import dataclass
import heapq
import math

from .messages import finite, positive

Cell = tuple[int, int]
Point = tuple[float, float]


@dataclass(frozen=True)
class GridMap:
    width: int
    height: int
    resolution: float
    blocked: frozenset[Cell] = frozenset()

    def __post_init__(self):
        if any(type(v) is not int or v <= 0 for v in (self.width, self.height)):
            raise ValueError('grid dimensions must be positive integers')
        positive(self.resolution)
        object.__setattr__(self, 'blocked', frozenset(self.blocked))
        for cell in self.blocked:
            if not self.contains(cell):
                raise ValueError('blocked cell lies outside grid')

    def contains(self, cell: Cell) -> bool:
        return (len(cell) == 2 and all(type(v) is int for v in cell)
                and 0 <= cell[0] < self.width and 0 <= cell[1] < self.height)

    def free(self, cell: Cell) -> bool:
        return self.contains(cell) and cell not in self.blocked

    def world(self, cell: Cell) -> Point:
        if not self.contains(cell):
            raise ValueError('cell outside grid')
        return ((cell[0] + 0.5) * self.resolution,
                (cell[1] + 0.5) * self.resolution)

    def cell(self, x: float, y: float) -> Cell:
        finite(x, y)
        return math.floor(x / self.resolution), math.floor(y / self.resolution)

    def inflate(self, radius: float) -> 'GridMap':
        finite(radius)
        if radius < 0:
            raise ValueError('inflation radius cannot be negative')
        if radius == 0:
            return self
        # Conservative square inflation; also reserves clearance at map borders.
        margin = math.ceil(radius / self.resolution)
        blocked = set(self.blocked)
        for x in range(self.width):
            for y in range(self.height):
                if min(x, y, self.width - 1 - x, self.height - 1 - y) < margin:
                    blocked.add((x, y))
        for x, y in self.blocked:
            for dx in range(-margin, margin + 1):
                for dy in range(-margin, margin + 1):
                    if self.contains((x + dx, y + dy)):
                        blocked.add((x + dx, y + dy))
        return GridMap(self.width, self.height, self.resolution, frozenset(blocked))

    def neighbors(self, cell: Cell):
        x, y = cell
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                       (1, 1), (1, -1), (-1, 1), (-1, -1)):
            neighbor = (x + dx, y + dy)
            if not self.free(neighbor):
                continue
            if dx and dy and (not self.free((x + dx, y)) or not self.free((x, y + dy))):
                continue
            yield neighbor, math.hypot(dx, dy)


def astar(grid: GridMap, start: Cell, goal: Cell) -> list[Cell]:
    if not grid.free(start) or not grid.free(goal):
        raise ValueError('start and goal must be free cells')
    costs = {start: 0.0}
    parents: dict[Cell, Cell] = {}
    frontier = [(math.dist(start, goal), 0.0, start)]
    while frontier:
        _, cost, cell = heapq.heappop(frontier)
        if cost > costs[cell]:
            continue
        if cell == goal:
            path = [goal]
            while path[-1] != start:
                path.append(parents[path[-1]])
            return list(reversed(path))
        for neighbor, step_cost in grid.neighbors(cell):
            candidate = cost + step_cost
            if candidate < costs.get(neighbor, math.inf):
                costs[neighbor] = candidate
                parents[neighbor] = cell
                heapq.heappush(frontier, (candidate + math.dist(neighbor, goal), candidate, neighbor))
    raise ValueError('goal is unreachable')
