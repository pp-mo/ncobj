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


DEBUG_WRITES = False


def _save_nc_dim(ds, dim):
    if DEBUG_WRITES:
        print "Writing      dim: (in {}) {}".format(ds.path, dim.name)
    ds.createDimension(dim.name, 0 if dim.unlimited else dim.length)


def _save_nc_var(ds, var):
    if DEBUG_WRITES:
        print "Writing      var: (in {}) {}".format(ds.path, var.name)
    ds_var = ds.createVariable(var.name,
                               var.data.dtype,   # NB ?future?
                               dimensions=[dim.name for dim in var.dimensions])
    ds_var[...] = var.data[...]
    for attr in var.attributes:
        _save_var_attr(ds_var, attr)


def _save_nc_attr(ds, attr):
    if DEBUG_WRITES:
        print "Writing     attr: (in {}) {}".format(ds.path, attr.name)
    ds.setncattr(attr.name, attr.value)


def _save_var_attr(ds_var, attr):
    if DEBUG_WRITES:
        print "Writing var-attr: (in {}) {}".format(ds_var._name, attr.name)
    ds_var.setncattr(attr.name, attr.value)


def _save_group(ds, group):
    # order: dimensions, variables, attributes, sub-groups
    if DEBUG_WRITES:
        parent_path = getattr(ds.parent, 'path', '')
        print "Writing    group: (in {}) {}".format(parent_path, group.name)
    for dim in group.dimensions:
        _save_nc_dim(ds, dim)
    for var in group.variables:
        _save_nc_var(ds, var)
    for attr in group.attributes:
        _save_nc_attr(ds, attr)
    for subgroup in group.groups:
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
