"""
An abstract representation of NetCDF data for manipulation purposes.

The purpose of this is to allow arbitrary manipulation of NetCDF data,
decoupled from the NetCDF file API.

A separate 'nc_dataset' submodule provides an interface for reading and
writing this form to and from NetCDF4.Dataset objects.

The containment of elements within other elements is two-way navigable, so a
reference to any part of a data structure potentially references the entire
object.  This enables all elements to provide a "remove" method.
(For this purpose, Attributes are also full independent objects.)

Elements which may be the target of internal naming "references", such as
user-types and dimensions, can be either duplicate object references or
independent objects.  Any inconsistent references are automatically reconciled
when writing the dataset to an actual file.
This enables freely moving sections of data between files, with any
referenced elements being re-created as required.
However, to preserve the hiearchical structure of referencing within groups,
any referenced elements must must added and/or copied at the group level, as
automatically generated reference elements are created at the top level.

"""
import numpy as np


class NcObj(object):
    """
    An object representing a named information element in NetCDF.
    """
    def __init__(self, name=None):
        """
        Args:
        * name (string):
        The name of this element (unique within any containing element).

        """
        if name is None:
            name = ''
        self._name = name
        # The container this is in -- initially none.
        self._container = None

    @property
    def container(self):
        return self._container

    def is_definition(self):
        return self.container and self.container.is_definitions()

    @property
    def name(self):
        return self._name

    def rename(self, name):
        """
        Rename an Ncobj element.

        Args:
        * name (string):
            the new name for this element.

        Note: this affects the container, if it is in one, and can raise an
        error if the name already exists in the container.

        """
        if self.container:
            self.container.rename_element(self, name)
        else:
            # detached object.
            self._name = name

#    @abstract
#    def detached_copy(self):
#        """
#        Return an independent 'unlinked' copy of this element.
#        """

#    @abstract
#    def __eq__(self, other):
#        pass

    def remove(self):
        """Remove from the parent container (if any)."""
        if self.container:
            self.container.remove(self)

    def __ne__(self, other):
        return not (self == other)


def _prop_repr(obj, property_name):
    """Make an optional initialisation string for a property."""
    result = ''
    if hasattr(obj, property_name):
        val = getattr(obj, property_name)
        if val:
            result = '{}={!r}'.format(property_name, val)
    return result


class Dimension(NcObj):
    """A NetCDF dimension object."""
    def __init__(self, name, length=None):
        NcObj.__init__(self, name)
        self._length = length

    @property
    def length(self):
        return self._length

    def isunlimited(self):
        return self.length is None

    def detached_copy(self):
        return Dimension(name=self.name, length=self.length)

    def __str__(self):
        return '<Dimension "{}" = {}>'.format(self.name, self.length)

    def __repr__(self):
        return 'Dimension({}, length={})'.format(
            self.name, self.length,
            ', {}'.format(_prop_repr(self, 'container')))

    def __eq__(self, other):
        return other.name == self.name and other.length == self.length


class Attribute(NcObj):
    """A NetCDF attribute object."""
    def __init__(self, name, value):
        NcObj.__init__(self, name)
        self._value = value

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, newval):
        self._value = newval

    def detached_copy(self):
        return Attribute(name=self.name, value=self.value)

    def __eq__(self, other):
        # NOTE: attributes do not have a type.  Is this correct ???
        return other.name == self.name and other.value == self.value

    def __str__(self):
        return '<Attribute "{}" = {}>'.format(self.name, self.value)

    def __repr__(self):
        return 'Attribute({}, value={}{}{})'.format(
            self.name, self.value,
            ', {}'.format(_prop_repr(self, 'container')))


class Variable(NcObj):
    """A NetCDF variable object."""
    def __init__(self, name,
                 dimensions=None, type=None, data=None, attributes=None):
        NcObj.__init__(self, name)
        if dimensions is None:
            dimensions = []
        elif isinstance(dimensions, Dimension):
            dimensions = [dimensions]
        self.dimensions = dimensions
        self.attributes = NcAttributesContainer(attributes)
        if hasattr(type, 'detached_copy'):
            # Needed for user-types.
            type = type.detached_copy()
        self.type = type
        self.data = data

    def detached_copy(self):
        return Variable(name=self.name, type=self.type, data=self.data,
                        dimensions=[dim.detached_copy()
                                    for dim in self.dimensions],
                        attributes=self.attributes.detached_contents_copy())

    def __eq__(self, other):
        return (self.name == other.name and
                self.type == other.type and
                np.all(self.data == other.data) and
                self.dimensions == other.dimensions and
                self.attributes == other.attributes)

    def __str__(self):
        repstr = '<Variable "{}":'.format(self.name)
        repstr += ' dims=({})'.format(
            ', '.join(d.name for d in self.dimensions))
        repstr += ', data={}'.format(self.data)
        if self.attributes:
            repstr += ', attrs=({})'.format(
                ', '.join(str(a) for a in self.attributes))
        return repstr + ')'

    def __repr__(self):
        repstr = 'Variable({}, type={!r}'.format(self.name, self.type)
        if self.dimensions:
            repstr += ', dimensions={!r}'.format(self.dimensions)
        repstr += ', data={}'.format(self.data)
        repstr += ', {}'.format(_prop_repr(self, 'attributes'))
        repstr += ', {}'.format(_prop_repr(self, 'container'))
        return repstr + ')'


class NcobjContainer(object):
    """
    A generic (abstract) container object for NetCDF elements.
    """
    def __init__(self, contents=None, in_element=None):
        """
        Args:

        * contents (iterable):
            A set of elements specifying the initial contents.
        * in_element (:class:`NcObj'):
            The element that this container exists in (if any).
            If this is a group, then the container's elements are definitions
            in that group (and self.is_definitions() is True).

        Note: the containers mostly emulate a dictionary.  A variety of
        indexing methods are provided -- __setitem__, __getitem__,
        __delitem__, pop, add and remove (the last two take the element not
        the name).
        Use names() for the names, and iter() or list() for the contents.
        Assigning to an existing name is an error, so "self[name].name == name"
        is always true.  A blank name is also forbidden.
        len() is also supported.

        TODO: probably more constraints on names for NetCDF validity ??

        """
        self._in_element = in_element
        self._content = {}
        if contents:
            for element in contents:
                self.__setitem__(element.name, element.detached_copy())

#    @abstractproperty
#    _of_type = None

    @property
    def in_element(self):
        return self._in_element

    def is_definitions(self):
        return isinstance(self.in_element, Group)

    def _check_element_type(self, element):
        if not isinstance(element, self._of_type):
            raise TypeError('Element named "{}" is not a {}, so cannot be '
                            'included in  a {} container.'.format(
                                element.name,
                                self._of_type.__name__,
                                self.__class__.__name__))

    def _check_element_name(self, name):
        if not isinstance(name, basestring) or len(name) == 0:
            raise ValueError('invalid element name "{}"'.format(name))

    def detached_contents_copy(self):
        elements = [element.detached_copy()
                    for element in self._content.itervalues()]
        return self.__class__(contents=elements)

    def names(self):
        return self._content.keys()

    def __getitem__(self, name):
        return self._content[name]

    def get(self, name, default=None):
        return self._content.get(name, default)

    def _setitem_ref_or_copy(self, name, element, detached_copy=False):
        # Assign as self[name]=element, taking a copy if specified.
        self._check_element_type(element)
        self._check_element_name(name)
        if name in self.names():
            raise ValueError('An element named "{}" already exists.'.format(
                name))
        if detached_copy:
            # Make a de-referenced copy of the element to add in.
            element = element.detached_copy()
        else:
            # Adding this actual element. Remove from any existing.
            element.remove()
        element._name = name
        self._content[name] = element
        element._container = self

    def setitem_reference(self, name, element):
        """
        Put an element reference in the container, as _content[name]=value.

        This is a lower-level operation than __setitem__, with important
        side-effects on the 'element' arg: Whereas __setitem__ treats the
        assigned element simply as a value, of which it makes a detached copy,
        this method inserts the actual element specified (first removing it
        from any existing parent container).

        """
        self._setitem_ref_or_copy(name, element, detached_copy=False)

    def __setitem__(self, name, element):
        """
        Place an element in the container under a given name.

        Note: content is copied from the provided element.  To insert an
        actual existing NcObj, use :meth:`NcobjContainer.setitem_reference`.

        """
        self._setitem_ref_or_copy(name, element, detached_copy=True)

    def pop(self, name):
        result = self._content.pop(name)
        result._container = None
        return result

    def __delitem__(self, name):
        self.pop(name)

    def remove(self, element):
        if element not in self._content.values():
            raise KeyError(element)
        return self.pop(element.name)

    def add(self, element):
        """
        Place an element in the container under its existing name.
        """
        self[element.name] = element

    def add_allof(self, elements):
        for element in elements:
            self.add(element)

    def remove_allof(self, elements):
        for element in elements:
            self.remove(element)

    def __iter__(self):
        return self._content.itervalues()

    def __len__(self):
        return len(self._content)

    def __eq__(self, other):
        return (isinstance(other, NcobjContainer) and
                self._content == other._content)

    def __ne__(self, other):
        return not (self == other)

    def rename_element(self, element, new_name):
        element = self.remove(element)
        self.setitem_reference(new_name, element)

    def __str__(self):
        contents = ', '.join('{}'.format(el) for el in self)
        return '<NcContainer({}): {}>'.format(
            self._of_type.__name__, contents)


class Group(NcObj):
    def __init__(self, name='',
                 dimensions=None, variables=None, attributes=None,
                 sub_groups=None,
                 parent_group=None):
        NcObj.__init__(self, name)
        self._parent = parent_group
        self.dimensions = NcDimensionsContainer(dimensions, in_element=self)
        self.variables = NcVariablesContainer(variables, in_element=self)
        self.attributes = NcAttributesContainer(attributes, in_element=self)
        self.groups = NcGroupsContainer(sub_groups, in_element=self)
        for group in self.groups:
            group._parent = self

    #
    # TODO: remove all the structural operations related to definitions
    # resolution to a separate module, creating extra public API methods for
    # containers and Groups as necessary (may already have what's needed?).
    #

    # Publish which of our properties are simple definitions containers.
    # N.B. does *not* include 'groups'.
    definitions_property_names = ('dimensions', 'variables', 'attributes')

    @property
    def parent_group(self):
        return self._parent

    def treewalk_content(self, return_types=None):
        if return_types is None or isinstance(self, return_types):
            yield self
        for container in (self.dimensions,
                          self.variables,
                          self.attributes):
            for element in container:
                if return_types is None or isinstance(element, return_types):
                    yield element
        for group in self.groups:
            treewalk_content(group, return_types)

    def all_variables(self):
        return list(element for element in self.treewalk_content(Variable))

    def find_root_group(self):
        group = self
        while group.parent_group:
            group = group.parent_group
        return self

    def _find_existing_definition(self, element, container_prop_name):
        """
        Search groups upward for a definition matching the given element.

        Args:
        * element (:class:`NcObj`):
        element with required properties.  The definition must == this.
        * container_prop_name (string):
        name of the Group property to search for matching elements.

        Returns:
            An existing definition object, or None.

        """
        for own_el in getattr(self, container_prop_name):
            if own_el == element:
                # Found in self.
                return element

        # Not in self.  Look in parent, if any.
        if self.parent_group:
            return self.parent_group._find_existing_definition(
                element, container_prop_name)

        # We have no parent, so we are done (fail).
        return None

    def _find_or_create_definition(self, element, create_at_top=False):
        """
        Search the group and its parents for a definition matching the element.
        If not found, create one, and return that instead.

        Args:
        * element (:class:`NcObj`):
        The element to search for.

        Kwargs:
        * create_at_top (bool):
        If set, create any new references at the top Group level.  Otherwise
        (the default), create within the local Group.

        .. note::

            At present, only Dimension elements can be referenced.
            TODO: add support for UserTypes.

        """
        if isinstance(element, Dimension):
            container_propname = 'dimensions'
        else:
            raise ValueError('element {} is not of a valid reference '
                             'type.'.format(element))

        ref = self._find_existing_definition(element, container_propname)
        if not ref:
            # Not found: create one.
            # Work out which group to create in
            if create_at_top:
                group = self.find_root_group()
            else:
                group = self
            defs_container = getattr(group, container_propname)
            # Install the new definition in this group, and return it.
            defs_container.add(element)

        return ref

    def resolve_all_references(self, create_at_top=False):
        """
        Ensure that all references within the structure are links to actual
        definitions somewhere in the group hieararchy.

        If necessary, new definition elements are created within the groups.

        Kwargs:
        * create_at_top (bool):
        If set, place newly-created definitions in the root group.
        Otherwise (the default), create within the Group containing the
        reference.

        """
        # Resolve references within contained variables (only place for now),
        for var in self.all_variables():
            # Fix up the variable's dimensions (the only thing for now).
            # Snapshot dimensions, so we can change the container on the fly.
            dims = list(var.dimensions)
            # Replace all with proper definition references.
            for dim in dims:
                dim = self._find_or_create_definition(dim, create_at_top)
                # Note: we must use a low-level assignment to insert 'dim'
                # itself, rather than a detached copy of it.
                var.dimensions.setitem_reference(dim.name, dim)

    def __str__(self, indent=None):
        indent = indent or '  '
        strmsg = '<Group "{}":'.format(self.name)
        strmsg += '\n{}dims=({})'.format(indent, self.dimensions)
        strmsg += '\n{}vars=({})'.format(indent, self.variables)
        if self.attributes:
            strmsg += '\n{}attrs=({})'.format(indent, self.attributes)
        if self.groups:
            strmsg += ''.join('\n' + group.__str__(indent+'  ')
                              for group in self.groups)
        strmsg += '\n>'
        return strmsg


class NcAttributesContainer(NcobjContainer):
    """An attributes container."""
    _of_type = Attribute


class NcDimensionsContainer(NcobjContainer):
    """A dimensions container."""
    _of_type = Dimension


class NcVariablesContainer(NcobjContainer):
    """A variables container."""
    _of_type = Variable
    # TODO: wrap generic contents handling to allow specifying dims by name


class NcGroupsContainer(NcobjContainer):
    """A subgroups container."""
    _of_type = Group
