import cadquery as cq
import cattr
from attr import define

from wisp3d.pegboard import PegboardArrangement, Pegboard
from wisp3d.pegboard.pegboard import Hook
from wisp3d.script import Script, Build, ExportTarget
from wisp3d.script.export_target import BuildContext
from wisp3d.script.script import ScriptInput
from wisp3d.utility import ExactCqWrapper, Vec2, wrap_cq_object, log, ExactNum


class PegboardScript(Script):
    def create_build(self, input_data: ScriptInput) -> Build:
        prepare_target = ExportTarget(
            name="Prepare",
            resolve_func=lambda b: PegboardScript.make_arrangement(input_data, b),
        )
        make_assemble_target = ExportTarget(
            name="Make",
            resolve_func=PegboardScript.make_assembly,
            dependencies=[prepare_target],
        )
        export_to_step_target = ExportTarget(
            name="Export to .step",
            resolve_func=PegboardScript.export_to_step,
            dependencies=[make_assemble_target],
        )
        return Build().add_target(export_to_step_target)

    @staticmethod
    def make_arrangement(
        input_data: ScriptInput, context: BuildContext
    ) -> PegboardArrangement:
        pegboard = Pegboard.deserialize(input_data.root["pegboard"])
        arrangement = PegboardArrangement(pegboard)

        @define
        class HolderRowStructure:
            spool_thickness: list[ExactNum]
            expand: bool
            pos: Vec2

        holder_rows: list[HolderRowStructure] = cattr.structure(
            input_data.root["holders"], list[HolderRowStructure]
        )
        for row in holder_rows:
            arrangement.add_holders_row(
                Hook(), row.spool_thickness, expand=row.expand, pos=row.pos
            )

        for holder in arrangement.spool_holders:
            log().info(
                "Holder: (x: %g - %g), (y: %g - %g)",
                holder.rect.min_x,
                holder.rect.max_x,
                holder.rect.min_y,
                holder.rect.max_y,
            )

        return arrangement

    @staticmethod
    def make_assembly(
        context: BuildContext, arrangement: PegboardArrangement
    ) -> ExactCqWrapper:
        made_assembly = arrangement.make(wrap_cq_object(cq.Workplane("XY")))
        return made_assembly

    @staticmethod
    def export_to_step(context: BuildContext, asm: ExactCqWrapper):
        asm.save("pegboard.step")
