"""aa_module: A basic class for child objects.

This module provides the base infrastructure used by ApertureArray submodules
to expose a namespaced API (e.g. ``aa.plotting.*``, ``aa.coords.*``).

Key features
------------
- The :class:`AaBaseModule` class implements a small helper, ``_attach_funcs``,
  to dynamically attach plain functions to an instance as methods while keeping
  a clean, user-facing signature. It assumes the attached functions follow the
  convention ``def func(aa, *args, **kwargs)`` where ``aa`` is the parent
  :class:`~ska_ost_low_uv.postx.aperture_array.ApertureArray`.
- The function signatures are rewritten using ``makefun.with_signature`` to
  drop the leading ``aa`` parameter from introspected help, without changing the
  underlying call semantics. The original docstrings are preserved.
"""

import functools
import types
from inspect import signature
from types import MethodType

from makefun import wraps

from ska_ost_low_uv.utils import inspect_class_method


def rgetattr(obj, attr, *args):
    """Recursive version of getattr."""

    def _getattr(obj, attr):
        return getattr(obj, attr, *args)

    return functools.reduce(_getattr, [obj] + attr.split('.'))


def rsetattr(obj, attr, val):
    """Recursive version of setattr."""
    pre, _, post = attr.rpartition('.')
    return setattr(rgetattr(obj, pre) if pre else obj, post, val)


def find_class_methods(class_obj) -> list[str]:
    """Return a list of methods for a class.

    Args:
        class_obj: The class object to inspect.

    Returns:
        A list of method names and first line of their docstring.
    """
    method_list = []
    for attr_name in dir(class_obj):
        attr = getattr(class_obj, attr_name)
        if isinstance(attr, types.MethodType) and not attr_name.startswith('_'):
            # Handle cases where docstring might be None or empty
            doc = attr.__doc__
            if doc is None:
                doc = 'No description available'
            else:
                doc = doc.split('\n')[0].strip()
                if not doc:
                    doc = 'No description available'
            method_list.append(f'{attr_name}() - {doc}')
    return method_list


class AaBaseModule(object):
    """A basic class for ApertureArray child objects.

    Anything in a child Classes docstring will be added to the __repr__.
    Classes inheriting from this should have a name starting with `Aa`,
    e.g. `AaCoords`. They are 'attached' to the ApertureArray thusly::

        Class ApertureArray(object):
        def __init__(self, ...):
            self.coords       = AaCoords(self)

    When calling display() in ipython / jupyter, the __repr__ will print
    all the stuff in the docstring -- which should be useful to the user.
    e.g.::

        <Aperture Array module: coords>
        Coordinate utils.

        Provides the following:
            get_sun() - Get the position of the sun as a SkyCoord
            get_zenith() - Get the zenith as a SkyCoord
            get_alt_az() - Get the alt/az of a given SkyCoord
            generate_phase_vector() - Generate a phase vector toward a given SkyCoord
    """

    def __init__(self, name: str = 'aa_base_module'):
        """Initialize class.

        Args:
            name (str): Name of module.
            func_dict (str): A dictionary of functions to add, e.g.
        """
        self.name = name  # pragma: no cover

    def __repr__(self):
        """Print simple representation of class."""
        return f'<Aperture Array module: {self.name}>\n'

    def __submodules__(self) -> list[str]:
        """Return a list of child AaBaseModules within a class.

        Args:
            class_obj: The class object to inspect.

        Returns:
            A list of child AaBaseModules.
        """
        submodule_list = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if isinstance(attr, AaBaseModule) and attr_name != 'aa':
                doc = attr.__doc__.split('\n')[0]
                submodule_list.append(f'.{attr_name} - {doc}')
        return submodule_list

    def _attach_funcs(self, func_map: dict[str, callable]):
        """Attach free functions as instance methods with clean signatures.

        This helper binds a set of plain functions (that are written with the
        first parameter being the parent ``ApertureArray`` instance, usually
        named ``aa``) onto the current module instance as methods. For better
        usability and IDE support, the displayed signature is rewritten to hide
        that first ``aa`` parameter, while preserving the original docstring and
        other metadata.

        Args:
            func_map (dict[str, callable]): Mapping from the attribute name that
                should appear on the module (e.g. ``'plot_matrix'``) to a free
                function with signature like ``def plot_matrix(aa, *args, **kwargs)``.

        Notes:
            - The original function's docstring is preserved on the attached
              method.
            - The first positional parameter (assumed to be ``aa``) is removed
              from the exposed signature using ``makefun.with_signature`` so
              that IDEs, ``help()``, and doc tools show a natural API such as
              ``plot_matrix(*args, **kwargs)``.
            - At call time, the wrapped method injects ``self.aa`` as the first
              argument when delegating to the original function.
        """
        for local_name, func in func_map.items():

            @wraps(func)
            def wrapper(*args, __func=func, **kwargs):
                # Get the first parameter name from the function signature
                sig = signature(__func)
                first_param = list(sig.parameters.keys())[0]
                # Remove it from kwargs if present
                kwargs.pop(first_param, None)
                return __func(self.aa, *args, **kwargs)

            setattr(self, local_name, MethodType(wrapper, self))

    def _attach_funcs_update(self, func_map: dict[str, (callable, str)]):
        """Attach free functions as instance methods and update model attributes.

        This helper binds a set of plain functions (that are written with the
        first parameter being the parent ``ApertureArray`` instance, usually
        named ``aa``) onto the current module instance as methods. After calling
        the function, it updates a specified model attribute with the return value.
        The original docstring and metadata are preserved using ``functools.wraps``.

        Args:
            func_map (dict[str, (callable, str)]): Mapping from the attribute name that
                should appear on the module (e.g. ``'sim_vis_gsm'``) to a tuple of:
                - A free function with signature like ``def func(aa, *args, **kwargs)``
                - A string specifying the model attribute to update (e.g. ``'model.visibilities'``)

        Notes:
            - The original function's docstring is preserved on the attached
              method using ``functools.wraps``.
            - At call time, the wrapped method injects ``self.aa`` as the first
              argument when delegating to the original function.
            - After the function returns, the result is assigned to the specified
              model attribute using ``setattr``.
            - The method returns the function's return value.

        Example:
            func_dict = {
                'sim_vis_gsm': (simulate_visibilities_gsm, 'model.visibilities'),
                'sim_beam': (simulate_beam, 'model.beam')
            }
            self._attach_funcs_update(func_dict)
        """
        for local_name, (func, attr_name) in func_map.items():

            @wraps(func)
            def wrapper(*args, __func=func, __attr_name=attr_name, **kwargs):
                # Get the first parameter name from the function signature
                sig = signature(__func)
                first_param = list(sig.parameters.keys())[0]
                # Remove it from kwargs if present
                kwargs.pop(first_param, None)
                retval = __func(self.aa, *args, **kwargs)
                rsetattr(self, __attr_name, retval)
                return retval

            setattr(self, local_name, MethodType(wrapper, self))

    def help(self, show_init: bool = False):
        """Print help for this class module.

        Args:
            show_init (bool): If true, will print the __init__ method signature.
        """
        # Create a help string and populate it
        help_str = f'{self.__repr__()}\n{self.__doc__}'

        if show_init is True:
            signature = inspect_class_method(self, '__init__')
            help_str += f'\n\n{signature}'

        methods = find_class_methods(self)
        if len(methods) > 0:
            method_str = 'Provides the following methods:\n'
            method_str += '\n'.join(f'    {m}' for m in methods)
            help_str += f'\n\n{method_str}'

        if len(self.__submodules__()) > 0:
            submod_str = 'Provides the following sub-modules:\n'
            submod_str += '\n'.join(f'    {m}' for m in self.__submodules__())
            help_str += f'\n\n{submod_str}'

        print(help_str)
