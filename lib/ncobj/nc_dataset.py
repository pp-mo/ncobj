"""
Module for converting ncobj data to and from NetCDF Datasets.

"""
import netCDF4
import ncobj as nco
import ncobj.grouping as ncg


def _make_attribute(ds, attr_name):
    return nco.Attribute(attr_name, value=ds.getncattr(attr_name))


def _make_dimension(ds, dim_name):
    dim = ds.dimensions[dim_name]
    return nco.Dimension(name=dim_name,
                         length=len(dim),
                         unlimited=dim.isunlimited())


def _make_variable(ds, var_name, group):
    var = ds.variables[var_name]
    dims = []
    for dim_name in var.dimensions:
        dim = ncg.find_named_definition(group, dim_name, nco.Dimension)
        if dim is None:
            # TODO: this error could use a group-path-string adding.
            raise ValueError('Dimension "{}" of variable "{}" not found in '
                             'input file.'.format(dim_name, var_name))
        dims.append(dim)

    attrs = [nco.Attribute(attr_name, value=var.getncattr(attr_name))
             for attr_name in var.ncattrs()]

    new_var = nco.Variable(name=var_name,
                           attributes=attrs,
                           data=var,
                           dtype=None)  # N.B. for now, types are not working..
    for dim in dims:
        new_var.dimensions.append(dim)

    return new_var


def _make_group(name, ds):
    # Read Group components in the right order, so they cross-reference.

    group = nco.Group(name)

    # Read attributes.
    group.attributes.add_allof([_make_attribute(ds, name)
                                for name in ds.ncattrs()])

    # Read dimensions.
    group.dimensions.add_allof([_make_dimension(ds, name)
                                for name in ds.dimensions])

    # Read variables.
    for name in ds.variables:
        var = _make_variable(ds, name, group)
        group.variables.setitem_reference(var.name, var)

    # Read sub-groups.
    group.groups.add_allof([_make_group(name, ds.groups[name])
                            for name in ds.groups])

    return group


def read(dataset):
    """
    Read a dataset from a netCDF file.

    Args:

    * dataset (:class:`netCDF4.Dataset`):
        An open readable file to scan for information.

    Returns:
        A :class:`ncobj.Group` representing the entire dataset.

    .. note::

        The returned data retains references to the netCDF4 dataset, which
        therefore must remain open while any of that data may still be needed.
        (For this reason, we don't yet support read from a filepath string).

    """
    return _make_group('', dataset)


def _save_nc_dim(ds, dim):
    ds.createDimension(dim.name, 0 if dim.unlimited else dim.length)


_MAGIC_FILLVALUE_NAME = '_FillValue'


def _save_nc_var(ds, var):
    attr_names = var.attributes.names()
    if _MAGIC_FILLVALUE_NAME in attr_names:
        attr_names.remove(_MAGIC_FILLVALUE_NAME)
        fill_value = var.attributes[_MAGIC_FILLVALUE_NAME].value
    else:
        fill_value = None
    ds_var = ds.createVariable(var.name,
                               var.data.dtype,   # NB ?future?
                               dimensions=[dim.name for dim in var.dimensions],
                               fill_value=fill_value)
    ds_var[...] = var.data[...]
    for attr_name in sorted(attr_names):
        _save_var_attr(ds_var, var.attributes[attr_name])


def _save_nc_attr(ds, attr):
    ds.setncattr(attr.name, attr.value)


def _save_var_attr(ds_var, attr):
    ds_var.setncattr(attr.name, attr.value)


def _save_group(ds, group):
    # order: dimensions, variables, attributes, sub-groups
    for dim_name in sorted(group.dimensions.names()):
        _save_nc_dim(ds, group.dimensions[dim_name])
    for var_name in sorted(group.variables.names()):
        _save_nc_var(ds, group.variables[var_name])
    for attr_name in sorted(group.attributes.names()):
        _save_nc_attr(ds, group.attributes[attr_name])
    for subgroup_name in sorted(group.groups.names()):
        subgroup = group.groups[subgroup_name]
        ds_subgroup = ds.createGroup(subgroup.name)
        _save_group(ds_subgroup, subgroup)


def write(dataset, group):
    """
    Write a dataset to a netCDF file.

    Args:

    * dataset (:class:`netCDF4.Dataset` or string):
        An open writeable file, or a path string to create one.
        If a file was created, it is closed again afterwards.

    * group (:class:`ncobj.Group`):
        Data to write.  Note that this is passed to
        :func:`ncobj.grouping.complete`, which will usually modify it.

    .. note::

        Writing data into an existing file can obviously cause problems, but
        will equally obviously work fine in specific cases.

    """
    # Ready group for output first (any error should lead unchanged).
    ncg.complete(group)
    # Either save to the provided dataset, or open one and save to it.
    if isinstance(dataset, basestring):
        with netCDF4.Dataset(dataset, 'w') as ds:
            _save_group(ds, group)
    else:
        _save_group(dataset, group)
