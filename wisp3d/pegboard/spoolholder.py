from copy import copy
from decimal import Decimal

from attr import define, field

from wisp3d.utility import to_exact_single, to_exact_list, to_float, Rect, AnyNum
from .pegboard import Hook, Pegboard, Hole


@define
class SpoolHolder:
    pegboard: Pegboard = field()
    rect: Rect = field()
    hook: Hook = field()
    length = field(converter=to_exact_single, default=180.8)
    thickness = field(converter=to_exact_single, default=7.4)
    bumps_pos = field(converter=to_exact_list, factory=lambda: [49.6, 155.6])
    bump_height = field(converter=to_exact_single, default=17.6)
    bump_thickness = field(converter=to_exact_single, default=4.8)
    bump_width = field(converter=to_exact_single, default=16.8)
    separator_recess_depth = field(converter=to_exact_single, default=2)
    separator_bottom_tol = field(converter=to_exact_single, default=0.2)
    separator_r1 = field(converter=to_exact_single, default=20)
    separator_l1 = field(converter=to_exact_single, default=15)
    separator_pos = field(converter=to_exact_single, default=0)
    separator_thickness = field(converter=to_exact_single, default=5)
    fillet_outer_r1 = field(converter=to_exact_single, default=20)

    # Preconditions:
    #   XY: the recess top surface
    #   Z+ is the recess top, Z- is the recess bottom
    # Returns the recess (that has to be subtracted) & the recess key (that has to be added)
    @staticmethod
    def make_recess(
        wp, offset: AnyNum, depth: AnyNum, d1: AnyNum, delta: AnyNum, tolerance=None
    ):
        offset, depth, d1, delta, tolerance = to_float(
            offset, depth, d1, delta, tolerance
        )

        def mk(tol: float):
            # Shrink sizes by tolerance
            offset_s = (offset[0] + tol, offset[1] + tol, offset[2])
            depth_s = depth - tol
            d1_s = (d1[0] - tol * 2, d1[1] - tol * 2)
            d2_s = (d1_s[0] - delta[0], d1_s[1] - delta[1])
            return (
                wp.transformed(offset=offset_s)
                .rect(*d1_s, centered=False)
                .transformed(offset=(delta[0] / 2, delta[1] / 2, -depth_s))
                .rect(*d2_s, centered=False)
                .loft()
            )

        return mk(0), mk(tolerance)

    # Preconditions:
    # XZ = pegboard front plane, +X = right, +Z = up, origin is pegboard lower left corner
    # Y directed inside pegboard
    def make(self, wp):
        # X+ = old Y+ = inside pegboard
        # Y+ = old Z+ = up
        # Z+ = old X+ = right
        hwp = wp.transformed(
            rotate=(0, 90, 90), offset=(self.rect.min_x, 0, self.rect.min_y)
        )
        holder_result = (
            wp.transformed()
        )  # Copy a workplane, we want to += to holder_result but not to wp

        # Create the separator main part
        separator_result = (
            hwp.transformed(offset=(0, 0, self.separator_pos))
            .moveTo(-self.fillet_outer_r1, self.thickness)
            .hLineTo(-self.length)
            .radiusArc(
                (-self.length + self.separator_r1, self.thickness + self.separator_r1),
                self.separator_r1,
            )
            .tangentArcPoint(
                (-self.thickness - self.separator_l1, self.rect.height), relative=False
            )
            .hLineTo(-self.thickness)
            .vLineTo(self.fillet_outer_r1)
            .tangentArcPoint((-self.fillet_outer_r1, self.thickness), relative=False)
            .close()
            .extrude(self.separator_thickness)
        )

        # Create the separator recess & the separator key (i.e. part that is inserted into a recess)
        side_recess, side_recess_key = self.make_recess(
            hwp.transformed(rotate=(0, -90, 0)),
            offset=(self.separator_pos, self.fillet_outer_r1, self.thickness),
            depth=self.separator_recess_depth,
            d1=(self.separator_thickness, self.rect.height - self.fillet_outer_r1),
            delta=(2 * self.separator_recess_depth, 0),
            tolerance=self.separator_bottom_tol,
        )
        bottom_recess, bottom_recess_key = self.make_recess(
            hwp.transformed(rotate=(-90, 0, 0)),
            offset=(
                -self.length,
                -self.separator_pos - self.separator_thickness,
                self.thickness,
            ),
            depth=self.separator_recess_depth,
            d1=(self.length - self.fillet_outer_r1, self.separator_thickness),
            delta=(0, 2 * self.separator_recess_depth),
            tolerance=self.separator_bottom_tol,
        )

        separator_result += side_recess_key
        separator_result += bottom_recess_key

        # Extrude a holder
        holder_result += (
            hwp.polyline(
                [
                    (0, self.fillet_outer_r1),
                    (0, self.rect.height),
                    (-self.thickness, self.rect.height),
                    (-self.thickness, self.fillet_outer_r1),
                ]
            )
            .tangentArcPoint((-self.fillet_outer_r1, self.thickness), relative=False)
            .polyline(
                [
                    (-self.fillet_outer_r1, self.thickness),
                    (-self.length, self.thickness),
                    (-self.length, 0),
                    (-self.fillet_outer_r1, 0),
                ]
            )
            .tangentArcPoint((0, self.fillet_outer_r1), relative=False)
            .close()
            .extrude(float(self.rect.width))
        )

        # Create a recesses for the separator
        holder_result -= side_recess
        holder_result -= bottom_recess

        # Add bumps
        for bump_center_x in self.bumps_pos:
            bump_outer_arc_r = self.bump_width / 2
            bump_outer_arc_top_height = self.bump_height
            bump_inner_arc_r = self.bump_width / 2 - self.bump_thickness
            bump_inner_arc_top_height = self.bump_height - self.bump_thickness
            bump_vline_height = self.bump_height - bump_outer_arc_r

            # Add a bump & remove recess for the separator under the bump
            holder_result += (
                hwp.center(-self.thickness - bump_center_x, self.thickness)
                .moveTo(-bump_outer_arc_r, 0)
                .vLineTo(bump_vline_height)
                .threePointArc(
                    (0, bump_outer_arc_top_height),
                    (bump_outer_arc_r, bump_vline_height),
                )
                .vLineTo(0)
                .hLineTo(bump_inner_arc_r)
                .vLineTo(bump_vline_height)
                .threePointArc(
                    (0, bump_inner_arc_top_height),
                    (-bump_inner_arc_r, bump_vline_height),
                )
                .vLineTo(0)
                .close()
                .extrude(self.rect.width)
                .moveTo(-bump_outer_arc_r, 0)
                .hLineTo(bump_outer_arc_r)
                .vLineTo(-self.thickness)
                .hLineTo(-bump_outer_arc_r)
                .close()
                .extrude(self.rect.width)
            )
            separator_result -= (
                hwp.center(-self.thickness - bump_center_x, self.thickness)
                .moveTo(-bump_outer_arc_r, -self.separator_recess_depth)
                .vLineTo(bump_vline_height)
                .threePointArc(
                    (0, bump_outer_arc_top_height),
                    (bump_outer_arc_r + self.separator_bottom_tol, bump_vline_height),
                )
                .vLineTo(-self.separator_recess_depth)
                .close()
                .offset2D(self.separator_bottom_tol)
                .extrude(self.rect.width)
            )

        # Find part of side that is not rounded, we can add hooks only to that part
        rect_with_hooks = copy(self.rect)
        rect_with_hooks.min_y += self.fillet_outer_r1
        rect_with_hooks.height -= self.fillet_outer_r1

        # Add hooks & make cuts for closed holes
        for hole in self.pegboard.find_holes_that_can_be_attached_to_rect_with_hook(
            rect_with_hooks, self.hook
        ):
            hole_centered_wp = wp.transformed(offset=(hole.center_x, 0, hole.center_y))
            if not hole.closed:
                # Add a hook
                holder_result += self.hook.make(hole_centered_wp, hole)
            else:
                # Hole is closed: cut holder around the hole
                cut_wp = wp.transformed(rotate=(90, 0, 0)).sketch()
                Hole.make_on_sketch(
                    cut_wp, [hole], mode="a", offset=hole.width * Decimal(1.2)
                )
                cut_wp = cut_wp.finalize()
                holder_result -= cut_wp.extrude(
                    max(self.fillet_outer_r1, self.thickness)
                )

        return holder_result, separator_result
