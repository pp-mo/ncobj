"""
Methods for dealing with the Group hierarchy.

"""
import ncobj
from ncobj import Group, Variable, Dimension, Attribute
from collections import namedtuple


def walk_group_objects(group, of_types=None):
    """
    Iterate over all contained components, recursively.

    Args:

    * of_types (type or iterable of types):
        If used, filter results by "isinstance(<element>, of_types)".

    Returns:
        an iterator

    """
    if of_types is None or isinstance(group, of_types):
        yield group
    for container in (group.dimensions,
                      group.variables,
                      group.attributes):
        for element in container:
            if of_types is None or isinstance(element, of_types):
                yield element

    for subgroup in group.groups:
        for obj in walk_group_objects(subgroup, of_types):
            yield obj


def all_variables(group):
    """Return a list of all enclosed :class:`~ncobj.Variable` definitions."""
    return list(walk_group_objects(group, Variable))


def all_dimensions(group):
    """Return a list of all enclosed :class:`~ncobj.Dimension` definitions."""
    return list(walk_group_objects(group, Dimension))


def all_groups(group):
    """Return a list of all sub-groups."""
    return list(walk_group_objects(group, Group))


def group_path(ncobj):
    """
    Return a string representing the absolute location of the element relative
    to the root group.

    Args:

    * ncobj (:class:`~ncobj.NcObj`)
        The element to locate.

    For example:
        group_path(<var>) --> "/group_A/var_X"

    """
    path = ncobj.name
    if ncobj.container and isinstance(ncobj.container.in_element, Group):
        path = group_path(ncobj.container.in_element) + '/' + path
    return path


def _find_definition(group, name, container_prop_name):
    """
    Search groups upward for a definition by name and container property name.

    Args:
    * group (:class:`~ncobj.Group`):
        The group to start searching at.

    * name (:class:`~ncobj.NcObj`):
        The name the element should have.

    * container_prop_name:
        The Group container property to look in.

    Returns:
        An existing definition object, or None.

    """
    for element in getattr(group, container_prop_name):
        if element.name == name:
            # Found in given group.
            return element

    # Not in this group:  Look in the parent (if any).
    if group.parent_group:
        return _find_definition(group.parent_group, name,
                                container_prop_name)

    # Group has no parent, so we are done (fail).
    return None


def find_named_definition(group, name, element_type):
    """
    Search groups upward for a definition by name and element type.

    Args:

    * group (:class:`~ncobj.Group`):
        The group to start searching at.

    * name (:class:`~ncobj.NcObj`):
        The name the element should have.

    * element_type (type):
        The element type (class) to search for (defines the relevant Group
        container attribute).

    Returns:
        An existing definition object, or None.

    """
    # Work out which Group property to search for this type of element.
    if issubclass(element_type, Dimension):
        container_prop_name = 'dimensions'
    elif issubclass(element_type, Variable):
        container_prop_name = 'variables'
    else:
        raise ValueError('type "{}" is not recognised, or not supported for '
                         'definition lookup'.format(element_type))

    return _find_definition(group, name, container_prop_name)


class DimensionConflictError(Exception):
    """Exception raised when dimension information is invalid."""
    pass


class NameConflictError(Exception):
    """Exception raised when names of components coincide."""
    pass


class IncompleteStructureError(Exception):
    """Exception raised when a required dimension definition is missing."""
    def __init__(self, var, dim):
        msg = ('Variable "{}" needs a dimension "{}", for which no definition '
               'exists in the group structure.'.format(
                   group_path(var), dim.name))
        super(IncompleteStructureError, self).__init__(msg)


# Check that all names within a group are compatible.
def check_group_name_clashes(group):
    """
    Check this group and subgroups for any name clashes between components.

    If found, raise a :class:`NameConflictError` describing the first clash.

    .. note::

        Name collisions can occur between variables, subgroups and user-types:
        In NetCDF, these components share a namespace within each group.

    """
    for grp in all_groups(group):
        var_names = set(group.variables.names())
        group_names = set(group.groups.names())
        clashes = var_names & group_names
        if clashes:
            badname = list(clashes)[0]
            raise NameConflictError('group "{}" contains both a variable and '
                                    'a subgroup named {}.'.format(
                                        group_path(grp), badname))


def add_missing_dims(group):
    """
    Create new definitions for any missing dimensions in the group.

    A missing dimension is one referred to by a variable in 'group' or its
    subgroups, for which no definition can be located by
    :func:`find_named_definition`.  The new ones are created in 'group'.

    Returns:
        A list of the definitions created for missing dimensions.

    .. note::

        If 'group' is not itself the root, then a matching definition may be
        found in a parent group.  In these cases, no new definition is created
        (even though the required definition is outside 'group').

    """
    # Find or create definitions for all dimensions used by all variables.
    new_created_dims = []
    for var in all_variables(group):
        for dim in var.dimensions:
            # Locate existing dimension in structure, if any.
            dim_def = find_named_definition(group, dim.name, Dimension)
            if dim_def is None:
                # Create a new top-level dimension definition.
                group.dimensions.add(dim)
                dim_def = group.dimensions[dim.name]
                # Keep a list, so we can remove again on error.
                new_created_dims.append(dim_def)
    return new_created_dims


def has_no_missing_dims(group, fail_if_not=False):
    """
    Check that matching definitions exist for all dimensions used in the
    variables of this group (and its sub-groups).

    Kwargs:

    * fail_if_not (bool):
        If set, then if and when a missing dimension is found, raise an
        :class:`IncompleteStructureError`, instead of just returning False.

    .. note::

        If 'group' is not itself the root, then a matching definition may be
        found in a parent group.  Such a dimension is not counted as 'missing'
        (even though the required definition is outside 'group').

    """
    for var in all_variables(group):
        for dim in var.dimensions:
            if not find_named_definition(var.container.in_element, dim.name,
                                         Dimension):
                if fail_if_not:
                    raise IncompleteStructureError(var, dim)
                return False
    return True


_DimVarData = namedtuple('DimVarsData', 'var dim')


def _add_dims_varsdata(group):
    # NOTE: only on completed structures (i.e. dim definitions all exist).
    has_no_missing_dims(group, fail_if_not=True)

    if not _has_varsdata(group):
        group._with_varsdata = True
        # Add blank data to every dimension definition.
        for dim in all_dimensions(group):
            dim._varsdata = []
        # Scan all variables and record usage against dimensions referenced.
        for var in all_variables(group):
            if not hasattr(var.data, 'shape'):
                # Take dims as given (lengths etc. may be unspecified)
                var_dims = var.dimensions
            else:
                # Construct dims modified by var shape where needed.
                shape = var.data.shape
                if len(shape) != len(var.dimensions):
                    raise DimensionConflictError(
                        'Variable {} has {} dimensions, but its data has {} '
                        'dimensions.'.format(group_path(var),
                                             len(var.dimensions),
                                             len(var.data.shape)))
                var_dims = [dim if shape[i_dim] == dim.length
                            else Dimension(dim.name, length=shape[i_dim],
                                           unlimited=dim.unlimited)
                            for i_dim, dim in enumerate(var.dimensions)]
            for dim in var_dims:
                # Locate the matching dimension definition in the structure.
                dim_def = find_named_definition(var.container.in_element,
                                                dim.name, Dimension)
                assert dim_def is not None
                # Add the variable with its dimension usage.
                dim_def._varsdata.append(_DimVarData(var, dim))


def _remove_dims_varsdata(group):
    for dim in all_dimensions(group):
        del dim._varsdata
    del group._with_varsdata


def _has_varsdata(group):
    return hasattr(group, '_with_varsdata')


def check_consistent_dims_usage(group):
    """
    Check that the requirements for all dimensions are consistent, and if not
    raise a :class:`DimensionConflictError`.

    This means that all references to each dimension must have the same length.
    Where variables have attached data, the length is taken from the data shape
    instead of the attached :class:`Dimension` object, and the number of
    dimensions must also match.  Each dimension must also have a known length,
    meaning that at least one reference must define the length, or have
    attached data.

    .. note::

        Can only be used on groups with no missing dimensions, as described for
        :func:`has_no_missing_dimensions`.
        Otherwise a :class:`IncompleteStructureError` will be raised.

    """
    has_existing_varsdata = _has_varsdata(group)
    if not has_existing_varsdata:
        _add_dims_varsdata(group)
    try:
        for dim in all_dimensions(group):
            # Look for conflicting requirements, which means defined (non-None)
            # lengths that don't match.
            # Different "unlimited" vals is not an error, so ignore those here.
            vars_dims = [var_dim for var_dim in dim._varsdata
                         if var_dim.dim.length is not None]
            if not vars_dims and dim.length is None:
                raise DimensionConflictError(
                    'No length can be deduced for dimension "{}".'.format(
                        group_path(dim)))
            # Complain if referencing variables disagree about the length.
            # NOTE: the dimension _itself_ may have a different length, this is
            # overridden by any length in the variables
            if len(vars_dims) > 1:
                var1, dim1 = vars_dims[0]
                for (varx, dimx) in vars_dims[1:]:
                    if dimx.length != dim1.length:
                        raise DimensionConflictError(
                            'Variable "{}" requires dimension "{}" = {}, but '
                            'variable "{}" requires "{}" = {}".'.format(
                                group_path(var1), dim1.name, dim1.length,
                                group_path(varx), dimx.name, dimx.length))
    finally:
        if not has_existing_varsdata:
            _remove_dims_varsdata(group)


def complete(group):
    """
    Make this group internally consistent, by adding any missing dimension
    definitions and linking all variable dimensions to their definitions.

    This makes the structure fully compliant with NetCDF constraints.  This
    ensures it is suitable to be written to a file.

    Dimension definitions are made consistent with the data and dimension
    information of all variables that reference them.  If this is not possible,
    as decribed for :func:`check_consistent_dims_usage`, a
    :class:`DimensionConflictError` is raised.
    A dimension definition will also be made 'unlimited' if any of the
    references requires it.

    .. note::

        A :class:`NameConflictError` can also result if components have
        conflicting names, as described for
        :func:`check_group_name_clashes`.

    """
    # NOTE: make dimensions unlimited when required, and also allow these to be
    # used where the variable information implies a fixed dimension.
    new_dim_defs = add_missing_dims(group)
    _add_dims_varsdata(group)
    try:
        check_consistent_dims_usage(group)
        check_group_name_clashes(group)
    except Exception:
        # Restore original argument before sending caller an exception.
        _remove_dims_varsdata(group)
        group.dimensions.remove_allof(new_dim_defs)
        raise

    # Fix properties of all dimension definitions from variables using them.
    for dim in all_dimensions(group):
        if dim._varsdata:
            # NOTE: do nothing to any unused dimensions here.
            # Can easily prune these if wanted.
            dims = [vardata.dim for vardata in dim._varsdata]
            lengths = [dimx.length for dimx in dims if dimx.length is not None]
            # Set length from variables, if any (else what it says in the dim).
            if lengths:
                # N.B. we already checked that all these lengths are the same.
                dim.length = lengths[0]
            # Likewise for 'unlimited'
            if any(dimx.unlimited for dimx in dims):
                dim.unlimited = True

    # Connect all variables' dims directly to dimension definitions.
    # (N.B. effectively the opposite of the 'detached' concept).
    for var in all_variables(group):
        var.dimensions = [find_named_definition(group, dim.name, Dimension)
                          for dim in var.dimensions]

    # Tidy up after.
    _remove_dims_varsdata(group)
