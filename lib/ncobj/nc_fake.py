"""
Module for wrapping an :class:`ncobj.Group` to make it as far as
possible appear as if it were a :class:`netCDF4.Dataset`.
This is for read-only purposes : all dataset-changing methods are missing.

At present this is focussed on delivering the ability to load these
quasi-datasets into the Iris project (https://github.com/SciTools/iris) :
The emulation of any behaviours *not* used there are currently uncertain.

"""

from collections import OrderedDict


class Nc4ComponentMimic(object):
    """Abstract class providing general methods for all mimic object types."""
    def __init__(self, nco_component, parent_grp=None):
        """Create a mimic object wrapping a :class:`nco.Ncobj` component."""
        self._ncobj = nco_component
        #: parent group object (mimic)
        self._parent_group_ncobj = parent_grp

    @property
    def name(self):
        return self._ncobj.name

    def group(self):
        return self._parent_group_ncobj

    def __eq__(self, other):
        return self._ncobj == other._ncobj

    def __ne__(self, other):
        return not self == other


def _name_as_string(obj_or_string):
    return (obj_or_string.name
            if hasattr(obj_or_string, 'name')
            else obj_or_string)


class DimensionMimic(Nc4ComponentMimic):
    """
    A Dimension object mimic wrapper.

    Dimension properties: name, length, unlimited, (+ parent-group)

    """
    @property
    def size(self):
        return 0 if self.isunlimited() else self._ncobj.length

    def __len__(self):
        return self.size

    def isunlimited(self):
        return self._ncobj.unlimited or not self._ncobj.length


class Nc4ComponentAttrsMimic(Nc4ComponentMimic):
    """An abstract class for an Nc4ComponentMimic with attribute access."""
    def ncattrs(self):
        return map(_name_as_string, self._ncobj.attributes)

    def getncattr(self, attr_name):
        if attr_name in self._ncobj.attributes.names():
            result = self._ncobj.attributes[attr_name].value
        else:
            raise AttributeError()
        return result

    def __getattr__(self, attr_name):
        return self.getncattr(attr_name)


class VariableMimic(Nc4ComponentAttrsMimic):
    """
    A Variable object mimic wrapper.

    Variable properties:
        name, dimensions, dtype, data (+ attributes, parent-group)
        shape, size, ndim

    """
    @property
    def dtype(self):
        return self._ncobj.data.dtype

    @property
    def datatype(self):
        return self.dtype

    @property
    def dimensions(self):
        return tuple(map(_name_as_string, self._ncobj.dimensions))

    def __getitem__(self, keys):
        if self.ndim == 0:
            return self._ncobj.data
        else:
            return self._ncobj.data[keys]

    @property
    def shape(self):
        return self._ncobj.data.shape

    @property
    def ndim(self):
        return self._ncobj.data.ndim

    @property
    def size(self):
        return self._ncobj.data.size


class GroupMimic(Nc4ComponentAttrsMimic):
    """
    A Group object mimic wrapper.

    Group properties:
        name, dimensions, variables, (sub)groups (+ attributes, parent-group)

    """
    def __init__(self, *args, **kwargs):
        super(GroupMimic, self).__init__(*args, **kwargs)

        self.dimensions = OrderedDict(
            [(dim.name, DimensionMimic(dim, parent_grp=self))
             for dim in self._ncobj.dimensions])

        self.variables = OrderedDict(
            [(var.name, VariableMimic(var, parent_grp=self))
             for var in self._ncobj.variables])

        self.groups = OrderedDict(
            [(grp.name, GroupMimic(grp, parent_grp=self))
             for grp in self._ncobj.groups])


class Nc4DatasetMimic(GroupMimic):
    def close(self):
        # ?should we not be doing "something" here ??
        return


def fake_nc4python_dataset(ncobj_group):
    """
    Make a wrapper around an :class:`ncobj.Group` object to emulate a
    :class:`netCDF4.Dataset'.

    The resulting :class:`GroupMimic` supports the essential properties of a
    read-mode :class:`netCDF4.Dataset', enabling an arbitrary netcdf data
    structure in memory to be "read" as if it were a file
    (i.e. without writing it to disk).

    In particular, variable data access is delegated to the original,
    underlying :class:`ncobj.Group` object :  This provides deferred, sectional
    data access on request, in the usual way, avoiding the need to read in all
    the variable data.

    """
    return Nc4DatasetMimic(ncobj_group)
