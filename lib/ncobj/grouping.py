"""
Methods for dealing with the Group hierarchy.

"""
from ncobj import Group, Variable, Dimension, Attribute
from collections import namedtuple


def walk_group_objects(group, of_types=None):
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
    return list(walk_group_objects(group, Variable))


def all_dimensions(group):
    return list(walk_group_objects(group, Dimension))


def all_groups(group):
    return list(walk_group_objects(group, Group))


def group_path(ncobj):
    path = ncobj.name
    if ncobj.container and isinstance(ncobj.container.in_element, Group):
        path = group_path(ncobj.container.in_element) + '/' + path
    return path


def _find_definition(group, name, container_prop_name):
    """
    Search groups upward for a definition by name and container property name.

    Args:
    * group (:class:`Group`):
        The group to start searching at.

    * name (:class:`NcObj`):
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
    * group (:class:`Group`):
        The group to start searching at.

    * name (:class:`NcObj`):
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
    else:
        raise ValueError('type "{}" is not recognised, or not supported for '
                         'definition lookup'.format(element_type))

    return _find_definition(group, name, container_prop_name)


class DimensionConflictError(Exception):
    pass


class NameConflictError(Exception):
    pass


# Check that all names within a group are compatible.
def check_group_name_clashes(group):
    vv, dd, gg = ('variable', 'dimension', 'group')
    for grp in all_groups(group):
        for type1, type2 in ((vv, dd), (vv, gg), (dd, gg)):
            names1 = getattr(group, type1+'s').names()
            names2 = getattr(group, type2+'s').names()
            clashes = set(names1) & set(names2)
            if clashes:
                badname = list(clashes)[0]
                raise NameConflictError('group "{}" contains both a {} and a '
                                        '{} named {}.'.format(
                                            group_path(grp), type1, type2,
                                            badname))


def add_missing_dims(group):
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


_DimVarData = namedtuple('DimVarsData', 'var dim')


def _add_dims_varsdata(group):
    if not hasattr(group, '_with_varsdata'):
        group._with_varsdata = True
        # Add blank data to every dimension definition.
        for dim in all_dimensions(group):
            dim._varsdata = []
        # Scan all variables and record usage against dimensions referenced.
        for var in all_variables(group):
            for dim in var.dimensions:
                # Locate existing dimension in structure, if any.
                dim_def = find_named_definition(group, dim.name, Dimension)
                assert dim_def is not None
                # Add the variable with its dimension usage.
                dim_def._varsdata.append(_DimVarData(var, dim))


def _remove_dims_varsdata(group):
    if hasattr(group, '_with_varsdata'):
        for dim in all_dimensions(group):
            del dim._varsdata
        del group._with_varsdata


def check_dims_usage_consistent(group):
    # Check that the requirements for all dimensions are consistent.
    has_existing_varsdata = hasattr(group, '_has_varsdata')
    try:
        if not has_existing_varsdata:
            _add_dims_varsdata(group)
        for dim in all_dimensions(group):
            if len(dim._varsdata) > 1:
                var1, dim1 = dim._varsdata[0]
                for (varx, dimx) in dim._varsdata[1:]:
                    if dimx.length != dim1.length:
                        raise DimensionConflictError(
                            'Variable "{}" requires dimension "{}={}", but '
                            'variable "{}" requires "{}={}"'.format(
                                group_path(var1), dim1.name, dim1.length,
                                group_path(varx), dimx.name, dimx.length))
    finally:
        if not has_existing_varsdata:
            _remove_dims_varsdata(group)


def complete(group):
    # Link all variable dimensions to definitions.
    # Resolve all dimensions to match variable sizes.
    # Check cross-class names.
    # NOTE: make dimensions unlimited when required, and also allow these to be
    # used where the variable information implies a fixed dimension.
    new_dim_defs = add_missing_dims(group)
    _add_dims_varsdata(group)
    try:
        check_dims_usage_consistent(group)
        check_group_name_clashes(group)
    except Exception:
        # Restore original argument before sending caller an exception.
        _remove_dims_varsdata(group)
        group.dimensions.remove_allof(new_dim_defs)
        raise

    # Fix properties of all dimension definitions from variables using them.
    for dim in all_dimensions(group):
        vardims = [vardata.dim for vardata in dim._varsdata]
        if vardims:
            # NOTE: do nothing to any unused dimensions here.
            # Can easily prune these if wanted.
            dim.length = vardims[0].length
            dim.unlimited = any(vardim.unlimited for vardim in vardims)

    # Connect all variables' dims directly to dimension definitions.
    # (N.B. effectively the opposite of the 'detached' concept).
    for var in all_variables(group):
        var.dimensions = [find_named_definition(group, dim.name, Dimension)
                          for dim in var.dimensions]

    # Tidy up after.
    _remove_dims_varsdata(group)
