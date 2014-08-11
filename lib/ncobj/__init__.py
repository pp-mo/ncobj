"""
An abstract representation of NetCDF data for manipulation purposes.

The purpose of this is to allow arbitrary manipulation of NetCDF data,
decoupled from the NetCDF file API.

For example:

with netCDF4.Dataset(file_in_path) as ds_in:
    in_group = ncobj.nc_dataset.read(ds_in)
    out_group = ncobj.Group()
    for var in in_group.variables:
        if var.name.startswith('my_'):
            out_group.variables.add(var)
    out_group.attributes.add(ncobj.Attribute('Notes', 'Subset for key=X.'))
    ncobj.nc_dataset.write(file_out_path, out_group)


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

.. note::

    Does not yet support extended (user) datatypes.

"""
from abc import ABCMeta, abstractmethod, abstractproperty


import numpy as np


__version__ = '0.2.x'


class NcObj(object):
    """
    A generic (abstract) object representing a named element, aka a NetCDF
    "component".

    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def detached_copy(self):
        """Return an independent 'unlinked' copy of this element."""
        pass

    @abstractmethod
    def __eq__(self, other):
        """Return whether equal to another."""
        pass

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
        """The :class:`NcobjContainer` this is in, if any."""
        return self._container

    def is_definition(self):
        """Return whether this element is a definition within a group."""
        return self.container and self.container.is_definitions()

    def definitions_group(self):
        """Return the Group in which this element is a definition, or fail."""
        if not self.is_definition():
            raise ValueError('element {} is not a definition: Its container '
                             'is {}.'.format(self, self._container))
        return self.container.in_element

    @property
    def name(self):
        """Name of the element."""
        return self._name

    def rename(self, name):
        """
        Rename the element.

        Args:

        * name (string):
            the new name for this element.

        .. note::

            This affects the container, if it is in one, and can raise an
            error if the name already exists in the container.

        """
        if self.container:
            self.container.rename_element(self, name)
        else:
            # detached object.
            self._name = name

    def remove(self):
        """
        Remove from the parent container, if any.

        """
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
            result = ', {}={!r}'.format(property_name, val)
    return result


class Dimension(NcObj):
    """A NetCDF dimension object."""
    def __init__(self, name, length=None, unlimited=False):
        NcObj.__init__(self, name)

        #: The length of the dimension.
        self.length = length

        #: Whether the dimension is unlimited.
        self.unlimited = unlimited

    def detached_copy(self):
        return Dimension(name=self.name, length=self.length,
                         unlimited=self.unlimited)

    def __str__(self):
        return '<Dimension "{}" = {}>'.format(self.name, self.length)

    def __repr__(self):
        return 'Dimension({}, length={}{}{})'.format(
            self.name, self.length,
            _prop_repr(self, 'container'),
            _prop_repr(self, 'unlimited'))

    def __eq__(self, other):
        return (isinstance(other, Dimension) and
                other.name == self.name and
                other.length == self.length and
                other.unlimited == self.unlimited)


class Attribute(NcObj):
    """A NetCDF attribute object."""
    def __init__(self, name, value):
        NcObj.__init__(self, name)

        #: The value of the attribute.
        self.value = value

    def detached_copy(self):
        return Attribute(name=self.name, value=self.value)

    def __eq__(self, other):
        # NOTE: attributes do not have a type.  Is this correct ???
        return (isinstance(other, Attribute) and
                other.name == self.name and other.value == self.value)

    def __str__(self):
        return '<Attribute "{}" = {}>'.format(self.name, self.value)

    def __repr__(self):
        return 'Attribute({}, value={}{})'.format(
            self.name, self.value,
            _prop_repr(self, 'container'))


class Variable(NcObj):
    """A NetCDF variable object."""
    def __init__(self, name,
                 dimensions=None, dtype=None, data=None, attributes=None):
        NcObj.__init__(self, name)
        if dimensions is None:
            dimensions = []
        elif isinstance(dimensions, Dimension):
            dimensions = [dimensions]

        #: :class:`Dimension` s of the variable.
        self.dimensions = list(dimensions)

        #: :class:`Attribute` s of the variable.
        self.attributes = NcAttributesContainer(attributes)

        if hasattr(dtype, 'detached_copy'):
            # Needed for user-types.
            dtype = dtype.detached_copy()
        self.dtype = dtype

        #: Variable data (indexable, with shape). Typically a
        #: :class:`NetCDF4.Variable`, or :class:`numpy.ndarray`.
        self.data = data

    def detached_copy(self):
        return Variable(name=self.name, dtype=self.dtype, data=self.data,
                        dimensions=[dim.detached_copy()
                                    for dim in self.dimensions],
                        attributes=self.attributes.detached_contents_copy())

    def __eq__(self, other):
        return (isinstance(other, Variable) and
                self.name == other.name and
                self.dtype == other.dtype and
                np.all(self.data == other.data) and
                self.dimensions == other.dimensions and
                self.attributes == other.attributes)

    def __str__(self):
        repstr = '<Variable "{}":'.format(self.name)
        repstr += ' dims=({})'.format(
            ', '.join(d.name for d in self.dimensions))
#        repstr += ', data={}'.format(self.data)
        if self.attributes:
            repstr += ', attrs=({})'.format(
                ', '.join(str(a) for a in self.attributes))
        return repstr + ')'

    def __repr__(self):
        repstr = 'Variable({}, dtype={!r}'.format(self.name, self.dtype)
        if self.dimensions:
            repstr += ', dimensions={!r}'.format(self.dimensions)
#        repstr += ', data={}'.format(self.data)
        repstr += _prop_repr(self, 'attributes')
        repstr += _prop_repr(self, 'container')
        return repstr + ')'


class NcobjContainer(object):
    """
    A generic (abstract) container object for :class:`NcObj` objects
    (aka "elements").

    """
    __metaclass__ = ABCMeta

    @abstractproperty
    # N.B. this should really also be *static*, but apparently can't have this
    # in Python 2.  Ref: http://bugs.python.org/issue5867
    def element_type(self):
        """The type (class) of elements this can contain."""
        return None

    def __init__(self, contents=None, in_element=None):
        """
        Args:

        * contents (iterable):
            A set of elements specifying the initial contents.

        * in_element (:class:`NcObj`):
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
            self.add_allof(contents)

    @property
    def in_element(self):
        """The element that this container exists in, if any."""
        return self._in_element

    def is_definitions(self):
        """
        Return whether this contains definitions in a :class:`Group`.

        """
        return isinstance(self.in_element, Group)

    def _check_element_type(self, element):
        if not isinstance(element, self.element_type):
            raise TypeError('Element named "{}" is not a {}, so cannot be '
                            'included in  a {} container.'.format(
                                element.name,
                                self.element_type.__name__,
                                self.__class__.__name__))

    def _check_element_name(self, name):
        if not isinstance(name, basestring) or len(name) == 0:
            raise ValueError('invalid element name "{}"'.format(name))

    def detached_contents_copy(self):
        """
        Return a copy of the container with detached copies of the elements.

        """
        elements = [element.detached_copy()
                    for element in self._content.itervalues()]
        return self.__class__(contents=elements)

    def names(self):
        """Return a list of names of the contained elements."""
        return self._content.keys()

    def __getitem__(self, name):
        """Return the named element."""
        return self._content[name]

    def get(self, name, default=None):
        """Return the named element, if any, or a default value."""
        return self._content.get(name, default)

    def _setitem_ref_or_copy(self, name, element, detached_copy=False):
        # Assign as self[name]=element, taking a copy if specified.
        # NOTE: *ALL* element-adding operations must come through here.
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

        This is a lower-level operation than
        :meth:`~NcobjContainer.__setitem__`, with important
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
        actual existing NcObj, use :meth:`~NcobjContainer.setitem_reference`.

        """
        self._setitem_ref_or_copy(name, element, detached_copy=True)

    def pop(self, name, *args):
        """Remove and return the named element, or return default."""
        if len(args) > 1:
            # behaviour of "pop" is slightly odd : can't use 'default=None'
            raise TypeError('pop expected at most 2 arguments, got {}'.format(
                1 + len(args)))
        if name in self._content:
            # Extract and detach.
            result = self._content.pop(name)
            result._container = None
        else:
            # Return supplied default, or fail if none given.
            if len(args):
                result = args[0]
            else:
                raise KeyError(name)
        return result

    def __delitem__(self, name):
        """Remove the named element."""
        self.pop(name)

    def remove(self, element):
        """Remove the matching element."""
        if element not in self._content.values():
            raise KeyError(element)
        return self.pop(element.name)

    def add(self, element):
        """Place an element in the container under its existing name."""
        self[element.name] = element

    def add_allof(self, elements):
        """Add multiple elements."""
        for element in elements:
            self.add(element)

    def remove_allof(self, elements):
        """Remove multiple elements."""
        for element in elements:
            self.remove(element)

    def __iter__(self):
        """Iterate over contents."""
        return self._content.itervalues()

    def __len__(self):
        """Return length."""
        return len(self._content)

    def __eq__(self, other):
        """Return whether equal to another."""
        return (isinstance(other, NcobjContainer) and
                other.element_type == self.element_type and
                self._content == other._content)

    def __ne__(self, other):
        return not (self == other)

    def rename_element(self, element, new_name):
        """Change content name (can raise KeyError)."""
        element = self.remove(element)
        self.setitem_reference(new_name, element)

    def __str__(self):
        contents = ', '.join('{}'.format(el) for el in self)
        return '<NcContainer({}): {}>'.format(
            self.element_type.__name__, contents)


class Group(NcObj):
    """A NetCdf Group object."""
    def __init__(self, name='',
                 dimensions=None, variables=None, attributes=None,
                 sub_groups=None,
                 parent_group=None):
        NcObj.__init__(self, name)
        self._parent = parent_group

        #: An :class:`NcDimensionsContainer` of dimensions in this Group.
        self.dimensions = NcDimensionsContainer(dimensions, in_element=self)

        #: An :class:`NcVariablesContainer` of variables in this Group.
        self.variables = NcVariablesContainer(variables, in_element=self)

        #: An :class:`NcAttributeContainer` of attributes in this Group.
        self.attributes = NcAttributesContainer(attributes, in_element=self)

        #: An :class:`NcGroupContainer` of subgroups of this Group.
        self.groups = NcGroupsContainer(sub_groups, in_element=self)
        for group in self.groups:
            group._parent = self

    @property
    def parent_group(self):
        """Return the parent Group of this, if any."""
        return self._parent

    # NOTE: at present, parent links are correctly established in __init__ and
    # detached_copy, but not automatically preserved by add+remove in
    # NcGroupsContainer.  This probably needs addressing.

    def detached_copy(self):
        return Group(name=self.name,
                     dimensions=self.dimensions,
                     variables=self.variables,
                     attributes=self.attributes,
                     sub_groups=self.groups,
                     parent_group=None)

    def __eq__(self, other):
        # Don't see a purpose for group equality ?
        return (isinstance(other, Group) and
                other.name == self.name and
                other.dimensions == self.dimensions and
                other.variables == self.variables and
                other.attributes == self.attributes and
                other.groups == self.groups)

    def __str__(self, indent=None):
        indent = indent or '  '
        strmsg = '<Group "{}":'.format(self.name)
        strmsg += '\n{}dims=({})'.format(indent, self.dimensions)
        strmsg += '\n{}vars=({})'.format(indent, self.variables)
        if self.attributes:
            strmsg += '\n{}attrs=({})'.format(indent, self.attributes)
        if self.groups:
            strmsg += ''.join('\n' + group.__str__(indent + '  ')
                              for group in self.groups)
        strmsg += '\n>'
        return strmsg


class NcAttributesContainer(NcobjContainer):
    """An :class:`Attribute` container."""
    @property
    def element_type(self):
        return Attribute


class NcDimensionsContainer(NcobjContainer):
    """A :class:`Dimension` container."""
    @property
    def element_type(self):
        return Dimension


class NcVariablesContainer(NcobjContainer):
    """A :class:`Variable` container."""
    @property
    def element_type(self):
        return Variable
        # TODO: wrap generic contents handling to allow specifying dims by name


class NcGroupsContainer(NcobjContainer):
    """A :class:`Group` container."""
    @property
    def element_type(self):
        return Group

    def _setitem_ref_or_copy(self, name, element, detached_copy=False):
        NcobjContainer._setitem_ref_or_copy(self, name, element,
                                            detached_copy=detached_copy)
        in_group = self.in_element
        if isinstance(in_group, Group):
            self[name]._parent = in_group

    def pop(self, name, *args):
        extract_ok = name in self._content
        result = NcobjContainer.pop(self, name, *args)
        if extract_ok:
            result._parent = None
        return result
