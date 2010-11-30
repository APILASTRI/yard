"""Utility classes that do not fit elsewhere"""

__author__  = "Tamas Nepusz"
__email__   = "tamas@cs.rhul.ac.uk"
__copyright__ = "Copyright (c) 2010, Tamas Nepusz"
__license__ = "MIT"

from collections import deque
from functools import wraps
from string import maketrans

import re


def axis_label(label):
    """Creates a decorator that attaches an attribute named ``__axis_label__``
    to a function. This is used later in the plotting functions to derive an
    appropriate axis label if the function is plotted on an axis.

    Usage::

        @axis_label("x squared")
        def f(x):
            return x ** 2
    """
    def result(func):
        func.__axis_label__ = label
        return func
    return result


def endless_generator(func, *args, **kwds):
    """Constructs an endless generator that yields elements generated by
    `func`. At each invocation, `func` should return a list of items
    that will be yielded one by one by this generator. Whenever the
    generator runs out of items, it will call `func` again for a new
    set of items. Additional positional and keyword arguments are passed
    on intact to `func`.
    """
    buffer = deque()
    while True:
        while buffer:
            yield buffer.popleft()
        buffer.extend(func(*args, **kwds))


def itersubclasses(cls, _seen=None):
    """Iterates over all subclasses of a given class, in depth first order.

    >>> list(itersubclasses(int)) == [bool]
    True
    >>> class A(object): pass
    >>> class B(A): pass
    >>> class C(A): pass
    >>> class D(B, C): pass
    >>> class E(D): pass
    >>> for cls in itersubclasses(A):
    ...      print(cls.__name__)
    ...
    B
    D
    E
    C
    >>> [cls.__name__ for cls in itersubclasses(object)] #doctest: +ELLIPSIS
    ['type',...'tuple',...]
    """

    if not isinstance(cls, type):
        raise TypeError("itersubclasses must be called with new-style "
                        "classes, not %.100r" % cls)
    if _seen is None:
        _seen = set()
    try:
        subs = cls.__subclasses__()
    except TypeError:
        subs = cls.__subclasses__(cls)
    for sub in subs:
        if sub not in _seen:
            _seen.add(sub)
            yield sub
            for sub in itersubclasses(sub, _seen):
                yield sub


def parse_size(size_as_string, dpi=72, sep='x,;'):
    """Parses a figure size specification and returns a figure size tuple that
    can be used in Matplotlib. The returned tuple will contain the figure width
    and height in inches.

    Figure size specifications consist of a width and a height specification,
    separated by an ``x``, a colon or a semicolon.  Whitespace does not matter.
    Widths and heights are considered to be in inches unless another measure is
    specified; the supported measures are as follows:

      - ``in``, ``inch``: inches

      - ``cm``: centimetres

      - ``mm``: millimetres

      - ``m``: metres

      - ``pt``: points

      - ``px``: pixels

    The conversion ratio between pixels and inches is given by the `dpi`
    parameter. It is also assumed that 1in = 72.27pt as this is the default in
    LaTeX.

    If either the width or the height is omitted, the missing measure is
    calculated from the other using the golden ratio such that the width
    is always the larger one. If both of them are missing, the width is
    assumed to be 8 inches and the width is calculated accordingly.

    You may specify an alternate set of separator characters using the
    `sep` argument. Any character found in `sep` will be considered a separator.

    Examples::

        >>> parse_size(None)           # doctest:+ELLIPSIS
        (8.0, 4.9442...)
        >>> parse_size('')             # doctest:+ELLIPSIS
        (8.0, 4.9442...)
        >>> parse_size('8x6')
        (8.0, 6.0)
        >>> parse_size('17 ; 24in', sep=';')
        (17.0, 24.0)
        >>> parse_size('20.32 Cm, 1016mm', sep=',')
        (8.0, 4.0)
        >>> parse_size('164px x 82px', dpi=41)
        (4.0, 2.0)
        >>> parse_size('8 yay 14.5', sep='ay')
        (8.0, 14.5)
        >>> parse_size('6in')          # doctest:+ELLIPSIS
        (6.0, 3.7082...)
    """
    if size_as_string is None:
        size_as_string = ''

    if "x" in sep:
        # If we have a pixel measure somewhere, we have to be careful
        size_as_string = size_as_string.replace("px", "PX")
        size_as_string = size_as_string.replace("Px", "PX")
    table = maketrans(sep, "_"*len(sep))
    size_as_string = size_as_string.translate(table)
    size_as_string = re.sub("_+", "_", size_as_string)
    width, _, height = size_as_string.partition("_")

    def find_measure_and_unit(measure):
        """Given a string containing a numeric measure and a unit,
        returns the measure as a number and the unit as a string,
        in a tuple."""
        measure = measure.strip().replace(" ", "")
        match = re.match("([-0-9.]+)([a-zA-Z]*)", measure)
        if not match:
            return None, None
        num = float(match.group(1))
        measure = match.group(2).lower()
        if not measure:
            measure = None
        return num, measure

    def convert_measure_to_inches(measure, unit):
        """Converts a measure-unit pair to a single number that
        represents the measure in inches."""
        if measure is None:
            return measure
        if unit is None:
            unit = "in"
        if unit == "in":
            # We already have inches
            return measure
        if unit == "cm":
            # Centimetres to inches
            return measure / 2.54
        if unit == "mm":
            # Millimetres to inches
            return measure / 254.0
        if unit == "m":
            # Metres to inches
            return measure / 0.0254
        if unit == "pt":
            # Points to inches
            return measure / 72.27
        if unit == "px":
            # Pixels to inches using the current dpi value
            return measure / float(dpi)
        raise ValueError("unsupported unit of length: %r" % unit)

    width, width_unit = find_measure_and_unit(width)
    height, height_unit = find_measure_and_unit(height)

    if width is None and height is None:
        width, width_unit = 8.0, "in"

    width, height = (convert_measure_to_inches(width, width_unit), 
                     convert_measure_to_inches(height, height_unit))
    
    if width is None:
        width = height * (1 + 5**0.5) / 2
    elif height is None:
        height = width * 2 / (1 + 5**0.5)

    return width, height


def vectorized(func):
    """Decorator that returns a vectorized variant of a single-argument
    function.
    """
    @wraps(func)
    def wrapper(item, *args, **kwds):
        if hasattr(item, "__iter__"):
            return [func(i) for i in item]
        return func(item)
    return wrapper

