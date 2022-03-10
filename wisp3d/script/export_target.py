from logging import Logger

from attr import define, field
from uuid import UUID, uuid4
from typing import Callable


class BuildContext:
    log: Logger


@define(eq=False)
class ExportTarget:
    name: str = field()
    resolve_func: Callable[[BuildContext, ...], object]
    id: UUID = field(factory=uuid4)
    dependencies: list["ExportTarget"] = field(factory=list)

    def compute(self, context: BuildContext, deps: list[object]):
        return self.resolve_func(context, *deps)
