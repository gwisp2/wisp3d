import abc
from typing import Any

import yaml
from attr import define

from .build import Build


@define
class ScriptInput:
    root: Any

    @staticmethod
    def from_yaml(content: str) -> "ScriptInput":
        root = yaml.safe_load(content)
        return ScriptInput(root)


class Script(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def create_build(self, input_data: ScriptInput) -> Build:
        pass
