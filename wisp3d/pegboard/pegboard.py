from itertools import groupby
from typing import List, Literal

import attr
from attr import define, field
import cattr
from wisp3d.utility import ExactCqWrapper, to_exact_single, Vec2, Rect, AnyNum, ExactNum


# Slot-shaped hole like holes on the IKEA SKADIS pegboards
@define
class Hole:
    center_x = field(converter=to_exact_single)
    center_y = field(converter=to_exact_single)
    width = field(converter=to_exact_single)
    height = field(converter=to_exact_single)
    closed: bool = field(default=False)

    def is_inside_rect(self, rect: Rect) -> bool:
        return (
            rect.min_x <= self.center_x - self.width / 2
            and self.center_x + self.width / 2 <= rect.max_x
            and rect.min_y <= self.center_y - self.height / 2
            and self.center_y + self.height / 2 <= rect.max_y
        )

    @staticmethod
    def make_on_sketch(
        wp: ExactCqWrapper, holes: List["Hole"], mode: str = "s", offset: AnyNum = 0
    ) -> ExactCqWrapper:
        # Divide holes into groups by size so that only one .slot call is needed for each group
        def hole_size_to_tuple(hole: Hole):
            return hole.width, hole.height

        holes = list(holes)
        holes.sort(key=hole_size_to_tuple)
        for group_key, group_elements in groupby(holes, hole_size_to_tuple):
            hole_w = group_key[0]
            hole_h = group_key[1]
            wp.push([(h.center_x, h.center_y) for h in group_elements])
            wp.slot(hole_h - hole_w, hole_w + 2 * offset, angle=90, mode=mode)
            wp.reset()

        return wp


# Hook that is used to fix something to a pegboard
@define
class Hook:
    length_z = field(converter=to_exact_single, default=12)
    width = field(converter=to_exact_single, default=4.5)
    height = field(converter=to_exact_single, default=4.5)
    gap_depth = field(converter=to_exact_single, default=5.25)
    full_depth = field(converter=to_exact_single, default=9.75)

    # Contact rectangle between a hook and an item
    def contact_rectangle(self, hole: Hole) -> Rect:
        install_y = hole.center_y + self.find_hook_install_height(hole)
        min_x = hole.center_x - self.width / 2
        min_y = install_y - self.height / 2
        return Rect(min_x, min_y, self.width, self.height)

    def find_hook_install_height(self, hole: Hole) -> ExactNum:
        # Not precise but ok for now: actual height may be lower
        return -hole.height / 2 + hole.width / 2 + self.height / 2

    # Preconditions:
    # XZ = pegboard front plane, +X = right, +Z = up
    # Y directed inside pegboard
    # Origin is a center of a hole front
    def make(self, wp, hole: Hole):
        install_z = self.find_hook_install_height(hole)
        box1 = wp.transformed(
            offset=(-self.width / 2, 0, -self.height / 2 + install_z)
        ).box(self.width, self.gap_depth, self.height, centered=False)
        box2 = wp.transformed(
            offset=(
                -self.width / 2,
                self.gap_depth,
                self.height / 2 - self.length_z + install_z,
            )
        ).box(
            self.width, self.full_depth - self.gap_depth, self.length_z, centered=False
        )
        return wp + box1 + box2


@define
class Pegboard:
    width: ExactNum = field(converter=to_exact_single)
    height: ExactNum = field(converter=to_exact_single)
    thickness: ExactNum = field(converter=to_exact_single)
    holes: ExactNum = field(factory=list)

    @staticmethod
    def deserialize(data):
        # Unstructure basic pegboard fields
        data_copy = dict(data)
        del data_copy["holes"]
        pegboard = cattr.structure(data_copy, Pegboard)

        # Unstructure holes data
        @define
        class HolesStructuredData:
            bottom_hole_center: Vec2
            interval: Vec2
            size: Vec2
            shift_per_row: ExactNum

        holes_data = data["holes"]
        hd: HolesStructuredData = cattr.structure(holes_data, HolesStructuredData)

        pegboard.add_holes(
            bottom_hole_center=hd.bottom_hole_center,
            interval=hd.interval,
            size=hd.size,
            shift_per_row=hd.shift_per_row,
        )

        return pegboard

    def add_holes(
        self,
        bottom_hole_center: Vec2,
        interval: Vec2,
        size: Vec2,
        shift_per_row: AnyNum,
    ) -> "Pegboard":
        shift_per_row = to_exact_single(shift_per_row)

        y = bottom_hole_center.y
        row_shift = 0
        while y <= self.height:
            row_start_x = (bottom_hole_center.x + row_shift) % interval.x
            x = row_start_x
            while x < self.width:
                hole = Hole(x, y, size.x, size.y)
                if hole.is_inside_rect(Rect(0, 0, self.width, self.height)):
                    self.holes.append(hole)
                x += interval.x
            y += interval.y
            row_shift += shift_per_row

        return self

    def make(self, wp):
        # Create a sketch
        s = wp.sketch()
        # Create pegboard rectangle
        s.push([(self.width / 2, self.height / 2)]).rect(
            self.width, self.height
        ).reset()
        # Cut holes
        Hole.make_on_sketch(s, self.holes, mode="s")
        # Extrude the sketch
        wp = s.finalize().extrude(-self.thickness)
        # Add discs that close the hole
        for hole in self.holes:
            if hole.closed:
                wp = (
                    wp.center(hole.center_x, hole.center_y)
                    .sketch()
                    .circle(hole.width * to_exact_single(1.4))
                    .rect(hole.width, 2, mode="s")
                    .finalize()
                    .extrude(5)
                )
        return wp

    def find_holes_that_can_be_attached_to_rect_with_hook(
        self, rect: Rect, hook: Hook
    ) -> List[Hole]:
        return [h for h in self.holes if hook.contact_rectangle(h).is_inside_of(rect)]

    # Expands rect so that it covers at least required_n_columns hole columns
    def expand_rect_x(
        self,
        rect: Rect,
        hook: Hook,
        required_n_columns: int,
        expand_dir: Literal["both", "left", "right"] = "both",
    ) -> Rect:
        def number_of_columns(holder_rect: Rect):
            return len(
                set(
                    h.center_x
                    for h in self.holes
                    if hook.contact_rectangle(h).is_inside_of(holder_rect)
                )
            )

        def candidate_score(holder_rect: Rect, expansion_candidate: Rect):
            return max(
                holder_rect.x_distance_to(expansion_candidate.min_x),
                holder_rect.x_distance_to(expansion_candidate.max_x),
            )

        expansion_dir_has_left = expand_dir in ["both", "left"]
        expansion_dir_has_right = expand_dir in ["both", "right"]

        # Find & sort holes to expand to
        expansion_candidates = list(
            c
            for h in self.holes
            for c in [hook.contact_rectangle(h)]
            if candidate_score(rect, c) != 0
            and (
                (expansion_dir_has_left and c.min_x < rect.min_x)
                or (expansion_dir_has_right and c.max_x > rect.max_x)
            )
        )
        expansion_candidates.sort(key=lambda c: -candidate_score(rect, c))

        # Do expansion
        while number_of_columns(rect) < required_n_columns and expansion_candidates:
            c = expansion_candidates.pop()
            rect = rect.expand_x(c.min_x).expand_x(c.max_x)

        return rect
