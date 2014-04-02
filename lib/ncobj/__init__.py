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


class NcObj(object):
    """
    An object representing a named information element in NetCDF.
    """
    def __init__(self, name, container=None, group=None):
        """
        Args:
        * name (string):
        The name of this element (unique within any containing element).
        * container (:class:`NcobjContainer`):
        A container that this element is held in.
        * group (:class:`Group`):
        The group that this element is defined in.

        """
        self._name = name
        self._container = container  # Parent container (if any)
        self._group = group  # Definition group (if any)

    @property
    def container(self):
        return self._container

    @property
    def name(self):
        return self._name

    def rename(self, name):
        """
        Rename an Ncobj element.

        Args:
        * name (string):
            the new name for this element.

        Note: this affects the group (NcContainer), if it is assigned to one,
        and will raise an error if the name already exists in the group.
        """
        if self.container:
            self.container.rename_element(self, name)
        else:
            # detached object.
            self.name = name

#    @abstract
    def detached_copy(self):
        """
        Return an independent 'unlinked' copy of this element.
        """
        pass

    def remove(self):
        """Remove from the parent container (if any)."""
        if self.container:
            self.container.pop(self, None)


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
    def __init__(self, name, length=None, group=None):
        NcObj.__init__(self, name, group)
        self.length = length

    def isunlimited(self):
        return self.length is None

    def detached_copy(self):
        return Dimension(name=self.name, length=self.length, group=None)

    def __str__(self):
        return '<Dimension "{}" = {}>'.format(self.name, self.length)

    def __repr__(self):
        return 'Dimension({}, length={}{})'.format(
            self.name,
            self.length,
            ', {}'.format(_prop_repr(self, 'group')))


class Attribute(NcObj):
    """A NetCDF attribute object."""
    def __init__(self, name, value, group=None):
        NcObj.__init__(self, name, group)
        self.value = value

    def detached_copy(self):
        return Attribute(name=self.name, value=self.value, group=None)

    def __str__(self):
        return '<Attribute "{}" = {}>'.format(self.name, self.value)

    def __repr__(self):
        return 'Attribute({}, value={}{}{})'.format(
            self.name,
            self.value,
            ', {}'.format(_prop_repr(self, 'container')),
            ', {}'.format(_prop_repr(self, 'group')))


class Variable(NcObj):
    """A NetCDF variable object."""
    def __init__(self, name,
                 dimensions=None, type=None, data=None, attributes=None,
                 group=None):
        NcObj.__init__(self, name, group)
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
        return Variable(name=self.name, group=None,
                        type=self.type, data=self.data,
                        dimensions=[dim.detached_copy()
                                    for dim in self.dimensions],
                        attributes=self.attributes.detached_contents_copy())

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
        repstr += ', {}'.format(_prop_repr(self, 'group'))
        return repstr + ')'


class NcobjContainer(object):
    """
    A generic (abstract) container object for NetCDF elements.
    """
    def __init__(self, contents=None, group=None):
        """
        Args:
        * contents (iterable):
        A set of elements specifying the initial contents.
        * group (:class:`Group'):
        The group that the container (and its elements) will belong to.

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
        self._group = group
        self._content = {}
        if contents:
            for element in contents:
                self.__setitem__(element.name, element.detached_copy())
                self._content[element.name]._container = self

    @property
    def group(self):
        return self._group

    def _check_element_type(self, element):
        if not isinstance(element, self._of_type):
            raise ValueError('Element named "{}" is not a {}, so cannot be '
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

    def __setitem__(self, name, element):
        """
        Place an element in the container under a given name.

        Note: content is copied from the provided element, and any grouped
        references are resolved (e.g. dimension references are imported into
        the group containing the 'self' element).
        """
        self._check_element_type(element)
        self._check_element_name(name)
        if name in self.names():
            raise ValueError('An element named "{}" already exists.'.format(
                name))
        # Add a de-referenced copy of the element to ourself.
        our_element = element.detached_copy()
        self._content[name] = our_element
        our_element._name = name
        our_element._container = self

    def pop(self, name, default=None):
        if name in self._content:
            element = self._content.pop(name)
            element._container = None
            result = element
        elif default:
            result = default
        else:
            raise KeyError(name)
        return result

    def __delitem__(self, name):
        self.pop(name)

    def add(self, element):
        """
        Place an element in the container under its existing name.
        """
        self[element.name] = element

    def remove(self, element):
        name = element.name
        own_element = self._content[name]
        if element is not own_element:
            raise KeyError(element)
        return self.pop(name)

    def __iter__(self):
        return self._content.itervalues()

    def __len__(self):
        return len(self._content)

    def rename_element(self, element, new_name):
        element = self.remove(element)
        element.name = new_name
        self[new_name] = element

    def __str__(self):
        contents = ', '.join('"{}":{}'.format(el.name, el) for el in self)
        return '<NcContainer({}): {}>'.format(
            self._of_type.__name__, contents)


class Group(NcObj):
    def __init__(self, name='', parent_group=None,
                 dimensions=None, variables=None, attributes=None,
                 sub_groups=None):
        NcObj.__init__(self, name, group=parent_group)
        self.dimensions = NcDimensionsContainer(dimensions, self)
        self.variables = NcVariablesContainer(variables, self)
        self.attributes = NcAttributesContainer(attributes, self)
        self.groups = NcGroupsContainer(sub_groups, self)

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
