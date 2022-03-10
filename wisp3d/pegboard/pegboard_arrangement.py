import cadquery as cq
from .pegboard import Pegboard, Hook
from .spoolholder import SpoolHolder
from wisp3d.utility import Rect, Vec2, AnyNum, to_exact_list, wrap_cq_object, log


class PegboardArrangement:
    pegboard: Pegboard
    spool_holders: list[SpoolHolder]

    def __init__(self, pegboard: Pegboard):
        self.pegboard = pegboard
        self.spool_holders = []

    def add_holders_row(
        self,
        hook: Hook,
        spools_thickness: list[AnyNum],
        expand: bool = True,
        pos: Vec2 = Vec2(0, 0),
    ):
        spools_thickness = to_exact_list(spools_thickness)

        separator_width = 5
        holder_height = 110
        required_spool_support_width = 10
        holder_bottom_y = pos.y

        requested_space = (
            sum(spools_thickness) + (len(spools_thickness) + 1) * separator_width
        )

        extra_space = self.pegboard.width - requested_space - pos.x
        if extra_space < 0:
            log().error("Not enough space for holders. Need %g mm more.", -extra_space)
            return

        if expand:
            extra_space_per_spool = extra_space / len(spools_thickness)
            log().info(
                "Extra space: %.1f mm, i.e. %.1f mm for each spool",
                extra_space,
                extra_space_per_spool,
            )
            # Since extra space is added for each spool we need to extend supports so that they still can hold a
            # normal-sized spool
            required_spool_support_width += extra_space_per_spool / 2

            # Widen spool thickness
            spools_thickness = [t + extra_space_per_spool for t in spools_thickness]

        # Add first spool holder
        holder_rect = Rect(
            pos.x,
            holder_bottom_y,
            separator_width + required_spool_support_width,
            holder_height,
        )
        holder_rect = self.pegboard.expand_rect_x(
            holder_rect, Hook(), 1, expand_dir="right"
        )
        self.spool_holders.append(
            SpoolHolder(
                pegboard=self.pegboard, rect=holder_rect, hook=hook, separator_pos=0
            )
        )
        last_spool_start_x = holder_rect.min_x + separator_width

        for i, spool_thickness in enumerate(spools_thickness):
            spool_end_x = last_spool_start_x + spool_thickness

            is_last_holder = i == len(spools_thickness) - 1

            # Calculate dimensions of a holder using basic requirements
            preliminary_holder_width = (
                separator_width
                + required_spool_support_width * (2 if not is_last_holder else 1)
            )
            preliminary_holder_x_start = spool_end_x - required_spool_support_width
            holder_rect = Rect(
                preliminary_holder_x_start,
                holder_bottom_y,
                preliminary_holder_width,
                holder_height,
            )

            # Expand holder width so that it has enough hooks to be fastened decently
            if not is_last_holder:
                holder_rect = self.pegboard.expand_rect_x(
                    holder_rect, hook, 2, expand_dir="both"
                )
            else:
                holder_rect = self.pegboard.expand_rect_x(
                    holder_rect, hook, 1, expand_dir="left"
                )

            # Calculate relative separator position
            holder_separator_pos = spool_end_x - holder_rect.min_x

            # Generate holder
            self.spool_holders.append(
                SpoolHolder(
                    pegboard=self.pegboard,
                    rect=holder_rect,
                    separator_pos=holder_separator_pos,
                    hook=hook,
                )
            )

            # Set last_spool_start_x to be used in the next iteration
            last_spool_start_x = spool_end_x + separator_width

    def make(self, xy_wp):
        pegboard_wp = xy_wp.transformed(rotate=(90, 0, 0))
        pegboard_wp = self.pegboard.make(pegboard_wp)
        asm = wrap_cq_object(cq.Assembly())

        asm.add(pegboard_wp, color=cq.Color("white"), name="Pegboard")

        for i, holder in enumerate(self.spool_holders):
            made_holder, made_separator = holder.make(xy_wp)
            name = f"H{i}"
            asm = asm.add(made_holder, color=cq.Color("green"), name=f"{name} - Holder")
            asm = asm.add(
                made_separator, color=cq.Color("blue"), name=f"{name} - Separator"
            )

        return asm
