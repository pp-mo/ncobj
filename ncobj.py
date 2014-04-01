class NcObj(object):
    """
    An object representing a named information element in NetCDF.
    """
    def __init__(self, name, parent=None, group=None):
        """
        Args:
        * name (string):
        The name of this element (unique within any containing element).
        * parent (:class:`NcobjContainer`):
        A container that this element is held in.
        * group (:class:`NcGroup`):
        The group that this element is defined in.

        """
        self.name = name
        self.parent = parent
        if group is None and parent is not None:
            group = parent.group
        self.group = group

    def group_path_in(self, in_group):
        """
        Construct a relative group-path to this object.

        Args:
        * in_group (:class:``):
        an NcGroup object to search for this item within.

        """
        # Find all super-groups of the requested containing in_group.
        supergroups = [in_group]
        group = in_group.group
        while group != None:
            supergroups.append(group)
            group = group.group

        # Scan our parents looking for a connection into the passed in_group.
        group_path = []
        group = self.group
        while group != None and group not in supergroups:
            group_path = [group.name] + group_path
            group = group.group
        if group is None:
            # No connection found with the requested in_group.
            return None
        else:
            # Found a connection.  Add '..' for groups "above" the requested.
            supergroups_iter = supergroups.iter()
            while supergroups_iter.next() != group:
                group_path = ['..'] + group_path
            return group_path

    def rename(self, name):
        """
        Rename an Ncobj element.

        Args:
        * name (string):
            the new name for this element.

        Note: this affects the group (NcContainer), if it is assigned to one,
        and will raise an error if the name already exists in the group.
        """
        if self.parent:
            self.parent.rename_element(self, name)
        else:
            # detached object.
            self.name = name

    @abstract
    def as_detached(self):
        """
        Return a 'detached' copy of this element.
        """
        pass

    def _match_references(self, source_element):
        # NOTE: default is do nothing.
        # Objects that may contain references (e.g. variables, which may
        # contain dimensions and user-types) must hook this to reproduce the
        # references within the source element in our own location
        pass

    def remove(self):
        """Remove from the group container (if any)."""
        if self.parent:
            self.parent.remove(self)

    def _added_to(self, container):
        """Record the parent container."""
        self.parent = container


class NcDimension(NcObj):
    """A NetCDF dimension object."""
    def __init__(self, name, group=None, length=None):
        NcObj.__init__(self, name, group)
        self.length = length

    def isunlimited(self):
        return self.length is None

    def detached_copy(self):
        return NcDimension(name=self.name, group=None, length=self.length)


class NcAttribute(NcObj):
    """A NetCDF attribute object."""
    def __init__(self, name, group=None, values):
        NcObj.__init__(self, name, group)
        self.values = values

    def detached_copy(self):
        return NcDimension(name=self.name, group=None, values=self.values)


class NcVariable(NcObj):
    """A NetCDF dimension object."""
    def __init__(self, name, group=None,
                 dimensions=None, dtype=None, data=None, attributes=None):
        NcObj.__init__(self, name, group)
        if dimensions is None:
            dimensions = []
        elif isinstance(dimensions, NcDimension):
            dimensions = [dimensions]
        self.dimensions = list(dimensions)
        self.attributes = NcAttributesContainer(attributes)
        if hasattr(dtype, 'as_detached'):
            # Needed for user-types.
            dtype = dtype.as_detached()
        self.dtype = dtype
        self._data = data

    def detached_copy(self):
        return NcVariable(name=self.name, group=None,
                          dimensions=[dim.detached_copy()
                                      for dim in self.dimensions],
                          attributes=self.attributes.detached_copy())

    def _match_references(self, source_element):
        pass
        # BIG TO-DO !


class NcobjContainer(object, Ncobj):
    """
    A generic (abstract) container object for NetCDF elements.
    """
    def __init__(self, contents=None, group=None):
        """
        Args:
        * contents (iterable):
        A set of elements specifying the initial contents.
        * group (:class:`NcGroup'):
        The group that the container (and its elements) will belong to.

        """
        NcObj.__init__(self, name, group)
        self._content = {}
        for element in contents:
            self.__setitem__(element.name, element.as_detached())
            self._content[element.name]._added_to(self.group)

    def _check_element_type(self, element):
        if not isinstance(element, self._of_type):
            raise ValueError('Element named "{}" is not a {}, so cannot be '
                             'included in  a {} container.'.format(
                                 element.name,
                                 self._of_type.__name__,
                                 self.__class__.__name__))

    def detached_copy(self):
        elements = [element.as_detached()
                    for element in self._content.itervalues()]
        return self.__class__(contents=elements)

    def names(self):
        return self._content.keys()

    def __getitem__(self, name):
        return self._contents[name]

    def __setitem__(self, name, element):
        """
        Place an element in the container under a given name.

        Note: content is copied from the provided element, and any grouped
        references are resolved (e.g. dimension references imported into
        the containing group).
        """
        if name in self.names():
            raise ValueError('An element named "{}" already exists.'.format(
                name))
        self._check_element_type(element)
        # Get a de-referenced copy of the element.
        our_element = element.as_detached()
        self._content[name] = our_element
        our_element.name = name
        # Resolve any path references within the new element.
        our_element._match_references(element)

    def add_element(self, element):
        """
        Place an element in the container under its existing name.
        """
        self[element.name] = element

    def remove_element(self, element):
        element = self._content.pop(element.name)
        element.group = None
        return element

    def pop(self, name):
        return self.remove_element(self[name])

    def __del__(self, name):
        self.remove_element(self[name])

    def rename_element(self, element, new_name):
        element = self.remove_element(element)
        element.name = new_name
        self[new_name] = element


class NcAttributesContainer(NcobjContainer):
    """An attributes container."""
    _of_type = NcAttribute


class NcDimensionsContainer(NcobjContainer):
    """A dimensions container."""
    _of_type = NcDimension


class NcVariablesContainer(NcobjContainer):
    """A variables container."""
    _of_type = NcVariable


class NcGroupsContainer(NcobjContainer):
    """A subgroups container."""
    _of_type = NcGroup


class NcGroup(NcObj):
    def __init__(self, name='', parent_group=None,
                 dimensions=None, variables=None, attributes=None,
                 sub_groups=None):
        NcObj.__init__(self, name, group=parent_group)
        self.dimensions = NcDimensionsContainer(dimensions, self)
        self.variables = NcVariablesContainer(variables, self)
        self.attributes = NcAttributesContainer(attributes, self)
        self.groups = NcGroupsContainer(sub_groups, self)


class NcFile(NcObj):
    def write(self, writable):
        pass

    def read(self, readable):
        pass

