"""
Example code based on ideas in
http://marqh.github.io/ncContainers/build/html/index.html

"""
from collections import namedtuple

import numpy as np

import ncobj.grouping as ncg
from ncobj.shorts import og, od, ov, oa


def _fake_complete(group):
    """
    'Complete' a group which is lacking some dimension lengths or data types.

    As the examples in simple_semantic_containers don't contain data, they
    don't have data types or lengths of unlimited dimensions (e.g. 'time').
    This operation sets missing lengths to 1, and fakes the data.
    This allows CDL to be generated (which needs the dtype), and variables to
    be compared (via "np.all(x.data == y.data)").

    This allows the examples builder functions to omit variables data, which is
    neater and saves space.

    """
    # Check all dims have definitions defined in the build code (for clarity).
    ncg.has_no_missing_dims(group, fail_if_not=True)

    # Fix up any top-level dims with no length (e.g. unlimited 'time').
    for dim in group.dimensions:
        if dim.length is None:
            dim.length = 1

    # Patch it all together.  Should work, now we have all the lengths.
    ncg.complete(group)

    # Add dummy data to variables without any.
    class _dummy_data(object):
        def __init__(self, shape, dtype=None):
            if dtype is None:
                dtype = np.dtype(np.float32)
            self.dtype = dtype
            self.shape = tuple(shape)

        def __eq__(self, other):
            return other.shape == self.shape

    for var in ncg.all_variables(group):
        if var.data is None:
            # NOTE: this might be better be done with numpy stride tricks ?
            var.data = _dummy_data(dim.length for dim in var.dimensions)


def eg_simple_grouped():
    """Produce a grouped version of the simple containers example."""
    d_lat = od('lat', 10)
    d_lon = od('lon', 5)
    d_time = od('time', u=True)
    dims = [d_lat, d_lon, d_time]

    c_lat = ov('lat', dd=[d_lat], aa=[oa('units', 'degrees_north')])
    c_lon = ov('lon', dd=[d_lon], aa=[oa('units', 'degrees_east')])
    c_time = ov('time', dd=[d_time], aa=[oa('units', 'seconds')])
    coords = [c_lat, c_lon, c_time]

    g = og('foo',
           dd=dims,
           gg=[og('instrument',
                  vv=(coords +
                      [ov('rh', dd=dims, aa=[oa('_FillValue', -1)])]),
                  aa=[oa('container_type', 'simple'),
                      oa('measurement_platform', 'aircraft')]),
               og('model',
                  vv=(coords +
                      [ov('rh', dd=dims, aa=[oa('_FillValue', -1)])]),
                  aa=[oa('container_type', 'simple'),
                      oa('measurement_platform',
                         'global circulation model')])])
    _fake_complete(g)
    return g


def eg_simple_flat():
    """Produce a flat version of the simple containers example."""
    d_lat = od('lat', 10)
    d_lon = od('lon', 5)
    d_time = od('time', u=True)
    dims = [d_lat, d_lon, d_time]

    collection_vars = [
        ov('instrument', data=np.array(0),
           aa=[oa('container_type', 'simple'),
               oa('members',
                  ('instrument___lat instrument___lon instrument___rh '
                   'instrument___time')),
               oa('measurement_platform', 'aircraft')]),
        ov('model', data=np.array(0),
           aa=[oa('container_type', 'simple'),
               oa('members',
                  'model___lat model___lon model___rh model___time'),
               oa('measurement_platform', 'global circulation model')])]

    data_vars = [
        ov('instrument___lat', dd=[d_lat], aa=[oa('units', 'degrees_north')]),
        ov('instrument___lon', dd=[d_lon], aa=[oa('units', 'degrees_east')]),
        ov('instrument___time', dd=[d_time], aa=[oa('units', 'seconds')]),
        ov('instrument___rh', dd=dims, aa=[oa('_FillValue', -1)]),
        ov('model___lat', dd=[d_lat], aa=[oa('units', 'degrees_north')]),
        ov('model___lon', dd=[d_lon], aa=[oa('units', 'degrees_east')]),
        ov('model___time', dd=[d_time], aa=[oa('units', 'seconds')]),
        ov('model___rh', dd=dims, aa=[oa('_FillValue', -1)])]

    g = og('foo', dd=dims, vv=collection_vars + data_vars)
    _fake_complete(g)
    return g


def flatten_grouped_containers(group):
    """Example operation, how to flatten a containers representation."""
    result = group.detached_copy()
    # get a list of the groups (because we alter while iterating)
    result_groups = list(result.groups)
    # represent groups as renamed variables with special container attributes
    for grp in result_groups:
        # Fail sub-sub-groups -- don't know how to deal with these ??
        assert not grp.groups
        # Also expect all dimensions at the top, not in groups ??for now??
        assert not grp.dimensions
        # Remove group from output, and add a container variable instead
        grp.remove()
        con_name = grp.name
        container_prefix = con_name + '___'
        con_attrs = grp.attributes.detached_contents_copy()
        # Add container special attributes
        if 'container_type' not in con_attrs.names():
            con_attrs.add(oa('container_type', 'simple'))
        sorted_names = sorted(grp.variables.names())
        if 'members' in con_attrs:
            # check the existing attribute matches the expected
            # NOTE: we are insisting on sorted order here
            var_names = sorted(grp.variables.names())
            memb_names = con_attrs['members']
            assert var_names == memb_names
            # remove it (we will be replacing with prefixed names)
            con_attrs.pop('members')
        # define (or redefine) the 'members' attribute
        con_attrs.add(oa('members',
                         ' '.join(container_prefix + var_name
                                  for var_name in sorted_names)))
        result.variables.add(ov(con_name,
                                aa=con_attrs,  # includes type+members
                                data=np.array(0)))
        # Add another output root variable for each of the groups members
        for var in grp.variables:
            var_tmp = var.detached_copy()
            # prepend group name to disambiguate variable names
            var_tmp.rename(container_prefix + var_tmp.name)
            result.variables.add(var_tmp)
    return result


def group_flat_containers(group):
    """Example operation, how to group a flat containers representation."""
    result = group.detached_copy()
    # find variables representing containers.
    con_vars = [var for var in ncg.all_variables(result)
                if 'container_type' in var.attributes.names()]
    # produce a group from each of these
    for con_var in con_vars:
        # container variables should have no dimensions.
        assert not con_var.dimensions
        # remove container variable and make a group instead
        con_name = con_var.name
        result.variables.remove(con_var)
        result.groups.add(og(con_name, aa=con_var.attributes))
        con_grp = result.groups[con_name]
        # remove redundant 'members' attribute inherited from container var
        con_grp.attributes.pop('members')
        # move member variables into the group (removing prefixes)
        prefix = con_name + '___'
        memb_names = con_var.attributes['members'].value.split(' ')
        for memb_name in memb_names:
            # remove member from root
            memb_var = result.variables.pop(memb_name)
            # strip initial disambiguation prefix, if present
            if memb_var.name.startswith(prefix):
                memb_name = memb_name[len(prefix):]
                memb_var.rename(memb_name)
            # place member in group
            con_grp.variables.add(memb_var)
    return result
