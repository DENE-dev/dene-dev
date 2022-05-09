############################################# IMPORTS #############################################

from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Tuple,
    Type,
    Union
)

from .utils import (
    isofclass,
    isoftype
)

############################################# GLOBALS #############################################

JSON_like_nottransposed = Union[list, dict]
JSON_like_transposed = Union[List[Objectify], Objectify, list]

JSON_like_any = Union[JSON_like_nottransposed, JSON_like_transposed]

############################################# CLASSES #############################################

class Objectify:
    """A more intuitive way to manipulate json-like dicts.
    Transforms any json-like `dict` into a both key and
    attribute-oriented class.
    This class is meant to have children, in which constructor
    takes class attributes as parameters, so that attribute
    type is always defined and unique.

    /!\ SUBCLASS MUST BE ANNOTATED WITH ATTRIBUTES AND
    THEIR TYPES, ELSE CONVERSION FROM Union[`dict`, `list`]
    TO Union[`Objectify`, List[`Objectify`]] WILL NEVER WORK.

    Example annotation format:
        class A(Objectify):
            b: B
            def __init__(self, b: B):
                super().__init__(b=b)

        class B(Objectify):
            c: List[C]
            def __init__(self, c: List[C]):
                super().__init__(c=c)

        class C(Objectify):
            d: int
            def __init__(self, d: int):
                super().__init__(d=d)

    Considering the above configuration, both syntaxes are
    equivalent: A['b'][0]['d'] <==> A.b[0].d

    """
    __annotations__ = {}

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __contains__(self, key: str) -> bool:
        """Returns key in self"""
        return key in self.keys()

    def __eq__(self, value: Any) -> bool:
        """Returns self == value"""
        return self._compile() == value

    def __getitem__(self, key: str) -> Any:
        """Returns self[key] (<==> self.key)"""
        return getattr(self, key)

    def __iter__(self) -> Iterable:
        """Returns iter(self)"""
        for key, value in self.items():
            if isinstance(value, Objectify):
                yield (key, dict(iter(value)))
            elif isinstance(value, (list, tuple)):
                yield (key, [dict(iter(x)) if isinstance(x, Objectify) else x for x in value])
            else:
                yield (key, value)

    def __len__(self) -> int:
        """Returns len(self)"""
        return len(self.keys())

    def __ne__(self, value: Any) -> bool:
        """Returns self != value"""
        return not self.__eq__(value)

    def __repr__(self) -> str:
        """Returns repr(self)"""
        return repr(self._compile())

    def __setitem__(self, key: str, value: Any):
        """Affects value to self[key] (hence self.key)"""
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            raise AttributeError

    def _compile(self) -> dict:
        """Compiles self in a dict structure"""
        d = {}
        for key, value in self.items():
            if isinstance(value, Objectify):
                d[key] = value._compile()
            elif isoftype(value, (List[Objectify], Tuple[Objectify])):
                d[key] = [x._compile() for x in value]
            else:
                d[key] = value

        return d

    def copy(self) -> "Objectify":
        """Same as dict.copy()"""
        d = {}
        for key, value in self.items():
            if isinstance(value, Objectify):
                d[key] = value.copy()
            else:
                d[key] = value
        return self.__class__(**d)

    def items(self) -> Iterable:
        """Same as dict.items()"""
        return self.__dict__.items()
    
    def keys(self) -> Iterable:
        """Same as dict.keys()"""
        return self.__dict__.keys()

    def values(self) -> Iterable:
        """Same as dict.values()"""
        return self.__dict__.values()

############################################ FUNCTIONS ############################################

def dictify(iterable: JSON_like_transposed) -> JSON_like_nottransposed:
    """Inverted operation: transforms any `Objectify`-composed
    data into an Union[`list`, `dict`]

    """
    if isinstance(iterable, Objectify):
        return iterable._compile()
    elif isoftype(iterable, List[Objectify]):
        return [x._compile() for x in iterable]
    elif isinstance(iterable, list):
        return [dictify(x) for x in iterable]
    else:
        return dict(iterable)

def objectify(
    iterable: JSON_like_transposed, cls: Type[JSON_like_transposed]
) -> JSON_like_transposed:
    """Transforms any json-like `dict` into a both key and
    attribute-oriented class.

    Parameters
        iterable: Union[`list`, `tuple`, `dict`]
            The instance to convert
        cls: Union[List[`Objectify`], `Objectify`, list]
            The type to convert instance to

    Returns
        Union[List[`Objectify`], `Objectify`, list]
            The converted instance to correct type

    Raises
        AttributeError
        TypeError

    """
    if isinstance(iterable, (list, tuple))\
       and isofclass(cls, (List[Objectify], Tuple[Objectify])):
        return [objectify(x, cls.__args__[0]) for x in iterable]

    elif isinstance(iterable, (Objectify, dict)) and isofclass(cls, Objectify):
        args = {}
        for arg, c in cls.__annotations__.items():
            if isofclass(c, Objectify):
                args[arg] = objectify(iterable[arg], c)
            elif isofclass(c, (List[Objectify], Tuple[Objectify])):
                args[arg] = [objectify(x, c.__args__[0]) for x in iterable[arg]]
            else:
                args[arg] = iterable[arg]

        return cls(**args)

    elif isoftype(iterable, cls):
        return iterable

    else:
        raise TypeError("Mismatch. Conversion pattern and data pattern don't seem alike.")