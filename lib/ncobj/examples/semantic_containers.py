"""
Example code based on ideas in
http://marqh.github.io/ncContainers/build/html/index.html

This version uses experimental extended concepts, designed to support multi-
layered subgrouping, container dimensions, and variable-name independence.

Container defined features:

* "container_type" behaves as before

* "container_dims" (in 'flat' form only) specifies (by name) dimensions
belonging to the container.
E.G. winds:container_dims = "winds___grid_x winds___grid_y" ;

* "container_vars" replaces "members", to specify contained variables in a
'flat' (i.e. group-less) container form, but may now also exist as an attribute
of a container group, to specify "role names", which were previously
implemented as arbitrarily-named extra attributes with meaning given in the
container specification.
E.G. :container_vars = "u=grid_winds_x v=grid_winds_y" ;

"""
from collections import namedtuple
import numpy as np

import ncobj as nco
import ncobj.grouping as ncg
from ncobj.shorts import og, od, ov, oa
from ncobj.examples.simple_semantic_containers import _fake_complete


def eg_simple_grouped():
    """Produce a grouped version of the simple containers example."""
    d_time = od('time', u=True)
    c_time = ov('time', dd=[d_time], aa=[oa('units', 'seconds')])

    d_ilat = od('lat', 10)
    d_ilon = od('lon', 5)
    idims = [d_ilat, d_ilon, d_time]
    d_mlat = od('lat', 24)
    d_mlon = od('lon', 16)
    mdims = [d_mlat, d_mlon, d_time]

    c_ilat = ov('lat', dd=[d_ilat], aa=[oa('units', 'degrees_north')])
    c_ilon = ov('lon', dd=[d_ilon], aa=[oa('units', 'degrees_east')])
    c_mlat = ov('lat', dd=[d_mlat], aa=[oa('units', 'degrees_north')])
    c_mlon = ov('lon', dd=[d_mlon], aa=[oa('units', 'degrees_east')])

    g = og('foo',
           dd=[d_time], vv=[c_time],
           gg=[og('instrument',
                  dd=[d_ilat, d_ilon],
                  vv=([c_ilat, c_ilon,
                       ov('rh', dd=idims, aa=[oa('_FillValue', -1)])]),
                  aa=[oa('container_type', 'simple'),
                      oa('measurement_platform', 'aircraft')]),
               og('model',
                  dd=[d_mlat, d_mlon],
                  vv=([c_mlat, c_mlon,
                       ov('rh', dd=mdims, aa=[oa('_FillValue', -1)])]),
                  aa=[oa('container_type', 'simple'),
                      oa('measurement_platform',
                         'global circulation model')])])
    _fake_complete(g)
    return g


def eg_simple_flat():
    """Produce a flat version of the simple containers example."""
    d_time = od('time', u=True)

    d_mlat = od('model___lat', 24)
    d_mlon = od('model___lon', 16)
    mdims = [d_mlat, d_mlon, d_time]
    d_ilat = od('instrument___lat', 10)
    d_ilon = od('instrument___lon', 5)
    idims = [d_ilat, d_ilon, d_time]

    collection_vars = [
        ov('instrument', data=np.array(0),
           aa=[oa('container_type', 'simple'),
               oa('container_dims', 'instrument___lat instrument___lon'),
               oa('container_vars',
                  'instrument___lat instrument___lon instrument___rh'),
               oa('measurement_platform', 'aircraft')]),
        ov('model', data=np.array(0),
           aa=[oa('container_type', 'simple'),
               oa('container_dims', 'model___lat model___lon'),
               oa('container_vars',
                  'model___lat model___lon model___rh'),
               oa('measurement_platform', 'global circulation model')])]

    data_vars = [
        ov('time', dd=[d_time], aa=[oa('units', 'seconds')]),
        ov('instrument___lat', dd=[d_ilat], aa=[oa('units', 'degrees_north')]),
        ov('instrument___lon', dd=[d_ilon], aa=[oa('units', 'degrees_east')]),
        ov('instrument___rh', dd=idims, aa=[oa('_FillValue', -1)]),
        ov('model___lat', dd=[d_mlat], aa=[oa('units', 'degrees_north')]),
        ov('model___lon', dd=[d_mlon], aa=[oa('units', 'degrees_east')]),
        ov('model___rh', dd=mdims, aa=[oa('_FillValue', -1)])]

    g = og('foo',
           dd=[d_mlat, d_mlon, d_ilat, d_ilon, d_time],
           vv=collection_vars + data_vars)
    _fake_complete(g)
    return g


REFERENCE_ATTRIBUTES_NAMES_AND_TYPES = [
    ('coordinates', nco.Variable),
    ('ancillary_variables', nco.Variable),
    ('bounds', nco.Variable),
    # ('cell_measures', nco.Variable),
    #    # N.B. form is wrong: "name: var"
    # ('cell_methods', nco.Variable),
    #   # N.B. even worse.
    #   # This starts to look like we will need associated encode/decode
    #   # methods for each reference attribute :-(
    # others:
    #   climatology, formula_terms, grid_mapping, instance_dimension
    ('container_vars', nco.Variable),
    ('container_dims', nco.Dimension)]


_RefTag = namedtuple('_RefTag', 'rolename reference')


# utility routines.

def split_noempties(str, split_at):
    # Do a string split, but ignore any repeats of the splitter
    return [elem for elem in str.split(split_at) if len(elem)]


def reftag_from_defstring(ref, in_group, ref_type):
    # Build a reftag from a definition string component
    names = split_noempties(ref, '=')
    if len(names) == 1:
        role_name, ref_name = None, names[0]
    else:
        # Note: if we had a=b=c=...=y=z, discard all but first + last
        role_name, ref_name = names[0], names[-1]
    ref = ncg.find_named_definition(in_group, ref_name, ref_type)
    return _RefTag(role_name, ref)


def defstring_from_reftag(reftag):
    # Make a container reference string element from a reftag
    if reftag.rolename:
        return '{}={}'.format(reftag.rolename, reftag.reference.name)
    else:
        return reftag.reference.name


def link_attribute_references(group):
    # Locate all variable and group attributes that contain variable
    # references (i.e. names), and replace their values with data containing
    # links to the actual variables, so we can reconstruct these attributes
    # after possibly renaming variables.
    groups_and_vars = ncg.all_variables(group) + ncg.all_groups(group)
    for elem in groups_and_vars:
        in_group = (elem if isinstance(elem, nco.Group)
                    else elem.container.in_element)
        assert isinstance(in_group, nco.Group)
        for ref_name, ref_type in REFERENCE_ATTRIBUTES_NAMES_AND_TYPES:
            attr = elem.attributes.get(ref_name, None)
            if attr:
                refs = split_noempties(attr.value, ' ')
                attr.value = [reftag_from_defstring(ref, in_group, ref_type)
                              for ref in refs]


def unlink_attribute_references(group, ref_attr_names_types=None):
    # Locate any variable and group attributes previously identified as
    # variable references, and reconstruct the attribute string from the names
    # of the referenced elements.
    groups_and_vars = ncg.all_variables(group) + ncg.all_groups(group)
    for elem in groups_and_vars:
        for ref_name, _ in REFERENCE_ATTRIBUTES_NAMES_AND_TYPES:
            attr = elem.attributes.get(ref_name, None)
            if attr:
                attr.value = ' '.join(defstring_from_reftag(reftag)
                                      for reftag in attr.value)


def flatten_grouped_containers(group):
    result = group.detached_copy()
    ncg.complete(result)
    link_attribute_references(result)
    _inner_flatten_grouped_containers(result)
    unlink_attribute_references(result)
    return result


def _inner_flatten_grouped_containers(result):
    # represent groups as renamed variables with special container attributes
    for grp in list(result.groups):  # list() because loop changes the object
        # Flatten any inner groups first.
        _inner_flatten_grouped_containers(grp)

        # Remove group from output, and create a container variable instead.
        con_name = grp.name
        con_prefix = con_name + '___'
        grp.remove()
        result.variables.add(ov(con_name, aa=grp.attributes, data=np.array(0)))
        con_var = result.variables[con_name]
        con_attrs = con_var.attributes

        # Add container type if not defined.
        if 'container_type' not in con_attrs.names():
            con_attrs.add(oa('container_type', 'simple'))

        # Check or add container_dims attribute.
        con_dims = [_RefTag(None, grp.dimensions[dim_name])
                    for dim_name in sorted(grp.dimensions.names())]
        if 'container_dims' in con_attrs.names():
            assert con_attrs['container_dims'].value == con_dims
        else:
            con_attrs.add(oa('container_dims', con_dims))

        # Move dimensions to the parent level, and rename them.
        for dim in list(grp.dimensions):  # list() because loop changes it
            result.dimensions.setitem_reference(con_prefix + dim.name, dim)

        # Check or add container_vars (aka "members") attribute.
        memb_vars = [_RefTag(None, grp.variables[name])
                     for name in sorted(grp.variables.names())]
        con_vars_attr = con_attrs.get('container_vars', None)
        if con_vars_attr:
            # Check the list matches the enclosed variables (sorted by name)
            role_vars = [_RefTag(None, var)
                         for role_name, var in con_vars_attr.value]
            assert role_vars == memb_vars
        else:
            con_attrs.add(oa('container_vars', memb_vars))

        # Move variables to the parent level, and rename.
        for var in list(grp.variables):  # list() because loop changes it
            result.variables.setitem_reference(con_prefix + var.name, var)

    return result


def group_flat_containers(group):
    result = group.detached_copy()
    ncg.complete(result)
    link_attribute_references(result)
    _inner_group_flat_containers(result)
    unlink_attribute_references(result)
    return result


def _inner_group_flat_containers(result):
    # Get variables representing containers (top-level only : recurse later).
    con_vars = [var for var in result.variables
                if 'container_type' in var.attributes.names()]
    # Translate each of these into an inner group.
    for con_var in con_vars:
        # Remove container variable and make a group instead.
        con_var.remove()
        con_name = con_var.name
        con_prefix = con_name + '___'
        result.groups.add(og(con_name, aa=con_var.attributes))
        con_grp = result.groups[con_name]
        con_attrs = con_grp.attributes

        # Remove dims attribute (if any) + process dims.
        dims_attr = con_attrs.pop('container_dims', None)
        if dims_attr:
            # Put dims into the group (removing name prefixes)
            for _, dim in dims_attr.value:
                # strip initial disambiguation prefix, if present
                dim_name = dim.name
                if dim_name.startswith(con_prefix):
                    dim_name = dim_name[len(con_prefix):]
                # Move into group with new name (N.B. this one, *not* a copy!)
                con_grp.dimensions.setitem_reference(dim_name, dim)

        # Move member variables into the group (removing prefixes).
        member_reftags = con_attrs['container_vars'].value
        for role_name, var in member_reftags:
            # strip initial disambiguation prefix, if present
            var_name = var.name
            if var_name.startswith(con_prefix):
                var_name = var.name[len(con_prefix):]
            # Move var into group with new name (N.B. this one, *not* a copy!)
            con_grp.variables.setitem_reference(var_name, var)
        # If container_vars attribute is redundant, remove it.
        if all(rolename is None for rolename, ref in member_reftags):
            del con_attrs['container_vars']

    # Lastly, process subgroups likewise to expand inner groups.
    for grp in result.groups:
        _inner_group_flat_containers(grp)

    return result
