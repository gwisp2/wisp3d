import logging
import sys
import contextlib
from typing import Optional

from attr import define, field
from uuid import UUID, uuid4
from logging import Logger, LoggerAdapter

from .export_target import ExportTarget, BuildContext
from wisp3d.utility import set_threadlocal_log_adapter, log


@define
class BuildContextImpl(BuildContext):
    build: "Build"
    current_target: Optional[ExportTarget] = field(default=None)
    _logger: Logger = field(init=False)

    def __attrs_post_init__(self):
        # Setup logger
        log_level = logging.DEBUG
        self._logger = logging.getLogger("build")
        self._logger.setLevel(log_level)
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(log_level)
        formatter = logging.Formatter("%(color)s%(indent)s%(message)s%(reset_color)s")
        ch.setFormatter(formatter)
        self._logger.addHandler(ch)

        # Setup logger adapter
        self.update_log_adapter()

    def update_log_adapter(self):
        blue = "\x1b[1;34m"
        green = "\x1b[1;32m"
        gray = "\x1b[0;37m"
        reset = "\x1b[0m"

        if self.current_target is not None:
            color = gray
            indent = "  "
        else:
            color = blue
            indent = ""

        # Set current logger adapter
        logger_adapter = LoggerAdapter(
            self._logger, extra={"indent": indent, "color": color, "reset_color": reset}
        )
        set_threadlocal_log_adapter(logger_adapter)

    @contextlib.contextmanager
    def set_target(self, target: ExportTarget):
        old_target = self.current_target
        self.current_target = target
        self.update_log_adapter()
        try:
            yield None
        finally:
            self.current_target = old_target
            self.update_log_adapter()


@define
class Build:
    id: UUID = field(factory=uuid4)
    targets: list[ExportTarget] = field(factory=list)
    artifacts: dict[ExportTarget, object] = field(factory=dict)
    context: BuildContext = field(init=False)

    def __attrs_post_init__(self):
        self.context = BuildContextImpl(build=self)

    def add_target(self, target: ExportTarget) -> "Build":
        if target in self.targets:
            # Target is already added
            return self

        # Add targets recursively
        for t in target.dependencies:
            self.add_target(t)
        self.targets.append(target)

        return self

    def resolve(self, target: ExportTarget) -> object:
        if target in self.artifacts:
            # Already resolved
            return self.artifacts[target]

        # Resolve dependencies
        resolved_deps = [self.resolve(dep) for dep in target.dependencies]

        log().info('Resolving target: "%s"', target.name)
        with self.context.set_target(target):
            # Resolve target in a context (context defined log messages format)
            self.artifacts[target] = target.compute(self.context, resolved_deps)
            return self.artifacts[target]

    def resolve_all(self):
        for target in self.targets:
            self.resolve(target)
