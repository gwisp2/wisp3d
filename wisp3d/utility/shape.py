from attr import define, field
from .exact_cq import to_exact_single, ExactNum
import cattr


# Exact rational 2D vector
@define(frozen=True)
class Vec2:
    x: ExactNum = field(converter=to_exact_single)
    y: ExactNum = field(converter=to_exact_single)

    def __add__(self, rhs: "Vec2") -> "Vec2":
        return Vec2(self.x + rhs.x, self.y + rhs.y)

    @staticmethod
    def deserialize(data) -> "Vec2":
        if len(data) != 2:
            raise ValueError("Data for Vec2 must have 2 arguments")
        return Vec2(data[0], data[1])


cattr.register_structure_hook(Vec2, lambda data, cl: Vec2.deserialize(data))


# Exact rational axis-aligned 2D rectangle
@define
class Rect:
    min_x: ExactNum = field(converter=to_exact_single)
    min_y: ExactNum = field(converter=to_exact_single)
    width: ExactNum = field(converter=to_exact_single)
    height: ExactNum = field(converter=to_exact_single)

    @property
    def max_x(self):
        return self.min_x + self.width

    @property
    def max_y(self):
        return self.min_y + self.height

    def expand_x(self, new_x) -> "Rect":
        min_x = min(new_x, self.min_x)
        max_x = max(new_x, self.max_x)
        return Rect(min_x, self.min_y, max_x - min_x, self.height)

    def x_distance_to(self, x: ExactNum) -> ExactNum:
        if self.min_x <= x <= self.max_x:
            return to_exact_single(0)
        else:
            return min(abs(self.min_x - x), abs(self.max_x - x))

    def is_inside_of(self, rhs: "Rect") -> bool:
        return (
            self.max_x <= rhs.max_x
            and self.max_y <= rhs.max_y
            and self.min_x >= rhs.min_x
            and self.min_y >= rhs.min_y
        )
