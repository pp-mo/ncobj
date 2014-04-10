"""
Methods for dealing with the Group hierarchy.

"""
from ncobj import Group, Variable, Dimension, Attribute


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
        walk_group_objects(subgroup, of_types)


def find_group_root(group):
    while group.parent_group:
        group = group.parent_group
    return group


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
        raise ValueError('type "{}" is not recognised or supported for '
                         'definition lookup'.format(name))

    return _find_definition(group, name, container_prop_name)


def _find_or_create_definition(group, element, create_missing_in_group=None):
    """
    Search the group and its parents for a definition matching the element.
    If not found, create one, and return that instead.

    Args:
    * element (:class:`NcObj`):
        The element to search for.

    Kwargs:
    * create_missing_in_group (:class:`Group`):
        If set, and no existing definition is found, create the new definition
        in this Group.  Otherwise (the default), put it in the starting group.

    .. note::

        At present, only Dimension elements can be referenced.
        TODO: add support for UserTypes.

    """
    # Work out which Group property to search for this type of element.
    if isinstance(element, Dimension):
        container_propname = 'dimensions'
    else:
        raise ValueError('element {} is not of a valid reference '
                         'type.'.format(element))

    # Work out where to put any newly created definitions.
    if create_missing_in_group is None:
        create_missing_in_group = group

    # See if there is an existing definition in the group structure.
    ref = find_element_definition(group, element, container_propname)
    if not ref:
        # Definition not found: create one.
        defs_container = getattr(create_missing_in_group, container_propname)
        # Install the new definition in this group, and return it.
        defs_container.add(element)
        ref = defs_container.get(element.name)

    return ref


def resolve_all_references(group, create_missing_in_group=None):
    """
    Ensure that all references within the structure are links to actual
    definitions somewhere in the group hieararchy.

    If necessary, new definition elements are created within the groups.

    Kwargs:
    * create_missing_in_group (:class:`Group`):
        If set, any missing definitions are created in this group.  Otherwise
        (the default), they are put in the groups of their parent variables.

    """
    # Resolve references within contained variables (only place for now),
    for var in walk_group_objects(group, Variable):
        # Fix up the variable's dimensions (the only thing for now).
        # Snapshot dimensions, so we can change the container on the fly.
        var_group = var.container.in_element
        assert isinstance(var_group, Group)
        dims = list(var.dimensions)
        # Replace all with proper definition references.
        for dim in dims:
            dim_definition = _find_or_create_definition(
                var_group, dim, create_missing_in_group)
            # Note: we must use a low-level assignment to insert 'dim'
            # itself, rather than a detached copy of it.
            var.dimensions.setitem_reference(dim.name, dim_definition)
