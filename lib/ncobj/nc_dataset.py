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


def read(file_source):
    # Read a dataset from a netCDF file.
    if isinstance(file_source, netCDF4.Dataset):
        # If a Dataset, use as-is.
        group = _make_group('', file_source)
    else:
        # Convert input to a NetCDF4 dataset + read that.
        with netCDF4.Dataset(file_source, 'r') as ds:
            group = _make_group('', ds)

    return group
