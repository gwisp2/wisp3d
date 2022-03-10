from fractions import Fraction
from typing import Union, List
import cadquery as cq

# Define type of exact number
import cattr

ExactNum = Fraction
AnyNum = Union[float, int, ExactNum]


# We need to convert tuples & lists of Fractions to floats (or possibly another types)
def convert_recursive(x, scalar_converter):
    if isinstance(x, tuple):
        return tuple(convert_recursive(e, scalar_converter) for e in x)
    elif isinstance(x, list):
        return list(convert_recursive(e, scalar_converter) for e in x)
    return scalar_converter(x)


def to_float(*args):
    return convert_recursive(args if len(args) != 1 else args[0], float)


def to_exact_single(num: AnyNum) -> ExactNum:
    return Fraction(num)


def to_exact_list(nums: List[AnyNum]) -> List[ExactNum]:
    return list(to_exact_single(n) for n in nums)


def to_exact(*args):
    return convert_recursive(args if len(args) != 1 else args[0], to_exact_single)


cattr.register_structure_hook(ExactNum, lambda data, cl: to_exact_single(data))


# CadQuery objects wrapper that converts fractions to floats when calling cq.Workplane or cq.Sketch methods
class ExactCqWrapper(object):
    def __init__(self, base):
        self._base = base

    def __getattribute__(self, name):
        if name == "_base":
            return object.__getattribute__(self, name)

        attr = object.__getattribute__(self._base, name)
        if hasattr(attr, "__call__"):

            def wrapper_func(*args, **kwargs):
                args, kwargs = ExactCqWrapper.convert_args(args, kwargs)
                result = attr(*args, **kwargs)
                return ExactCqWrapper.convert_result(result)

            return wrapper_func
        else:
            return attr

    def __add__(self, rhs):
        unwrapper_rhs = rhs._base if isinstance(rhs, ExactCqWrapper) else rhs
        return ExactCqWrapper(self._base + unwrapper_rhs)

    def __iadd__(self, rhs):
        unwrapper_rhs = rhs._base if isinstance(rhs, ExactCqWrapper) else rhs
        self._base += unwrapper_rhs
        return self

    def __sub__(self, rhs):
        unwrapper_rhs = rhs._base if isinstance(rhs, ExactCqWrapper) else rhs
        return ExactCqWrapper(self._base - unwrapper_rhs)

    def __isub__(self, rhs):
        unwrapper_rhs = rhs._base if isinstance(rhs, ExactCqWrapper) else rhs
        self._base -= unwrapper_rhs
        return self

    @staticmethod
    def convert_result(result):
        if (
            isinstance(result, cq.Workplane)
            or isinstance(result, cq.Sketch)
            or isinstance(result, cq.Assembly)
        ):
            return ExactCqWrapper(result)
        else:
            return result

    @staticmethod
    def convert_args(args, kwargs):
        args = tuple(ExactCqWrapper.convert_arg(arg) for arg in args)
        kwargs = {k: ExactCqWrapper.convert_arg(v) for k, v in kwargs.items()}
        return args, kwargs

    @staticmethod
    def convert_arg(arg):
        return convert_recursive(arg, ExactCqWrapper.convert_scalar_arg)

    @staticmethod
    def convert_scalar_arg(arg):
        if isinstance(arg, ExactCqWrapper):
            return arg._base
        if isinstance(arg, Fraction):
            return to_float(arg)
        return arg


def wrap_cq_object(w: Union[cq.Workplane, cq.Assembly, cq.Sketch]) -> ExactCqWrapper:
    return ExactCqWrapper(w)
