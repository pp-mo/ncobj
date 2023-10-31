"""
Copy data between two netCDF4 datasets.

This lets you make modified versions of data read from file.
It doesn't support Groups, so it's not full NETCDF4 compliant :-(
Can control which variables and (global) attributes are in- or ex-cluded.
(Or.. can just copy the lot and modify before closing.)

TODO:
  add proper tests for all the include/exclude stuff
  include tests for the include/exclude stuff
  add support for Groups.  N.B. don't have good test examples for this.
  add support for user-types.  N.B. don't have good test examples for this.

REPLACE:
  Existing code is a stop-gap for a better approach, which is decoupled from
  a _file_ and does *not* reflect all modifications back to one.
  Ideally want a "netCDF object" which can freely read-from/write to files.
    * should provide the things you *can't* do with netCDF4 itself...
    * so you can filter, augment or adjust and then write out elsewhere
      - for example, remove certain attributes of certain variables
    * each component is represented by an independent object (type)
        * these can be freely deleted, added, adjusted
        * renaming should also be possible
    * ideally, the variables will preserve deferred data access

ISSUES:
  some known problems with attributes in netCDF4 implementation
    -  e.g. distinguish 1.0 and [1.0] ?
    -  e.g. distinguish ["this", "that"] and "this that" ?

"""

import netCDF4


do_debug = True

def nc_copy(ds_from, ds_to,
            include_vars=None, exclude_vars=None,
            include_dims=None, exclude_dims=None,
            include_attrs=None, exclude_attrs=None):
    """
    Copy information between two open netCDF4 datasets.

    Copies selected data elements (variables, global dimensions and global
    attributes) from the input to the output netCDF4 Dataset.  A partial copy
    can also be specified.

    Args:

    * ds_from, ds_to (:class:`netCDF4.Dataset`):
        netCDF4 Datasets to copy between.  Must be open for reading and
        writing, as appropriate.

    Kwargs:

    * include_vars, exclude_vars (iterable of strings):
        Control which variables to copy.  The keys 'include_vars' and
        'exclude_vars' are mutually exclusive.  Default copies everything.

    * include_dims, exclude_dims (iterable of strings):
        Control which dimensions to copy.  The keys 'include_vars' and
        'exclude_vars' are mutually exclusive.  The default is to copy
        all dims which are used by any of the variables copied.

    * include_attrs, exclude_attrs (iterable of strings):
        Control which global attributes to copy. The keys 'include_attrs' and
        'exclude_attrs' are mutually exclusive.  Default copies everything.

    .. note::
        Any elements already exisiting in ds_out (i.e. of the same name) will
        *not* be written.

    .. note::
        Does not yet support netcdf-4 user-types or Groups.

    """
    if ds_from.groups:
        raise ValueError('source contains groups : not supported.')
    if include_vars and exclude_vars:
        raise ValueError('include_vars and exclude_vars cannot both be set.')
    if include_attrs and exclude_attrs:
        raise ValueError('include_attrs and exclude_attrs cannot both be set.')
    if include_dims and exclude_dims:
        raise ValueError('include_dims and exclude_dims cannot both be set.')
    varnames = set(ds_from.variables.keys())
    if include_vars:
        varnames = varnames & set(include_vars)
    elif exclude_vars:
        varnames = varnames - set(exclude_vars)
    varnames = varnames - set(ds_to.variables.keys())
    varnames = sorted(varnames)
    if do_debug:
        print 'Var names: ', varnames

    dimnames = set(ds_from.dimensions.keys())
    if include_dims:
        dimnames = dimnames & set(include_dims)
    elif exclude_dims:
        dimnames = dimnames - set(exclude_dims)
    else:
        # slightly more clever in this case : refer to the selected vars
        dimnames = set(d
                       for d in dimnames
                       if any([d in ds_from.variables[varname].dimensions
                               for varname in varnames]))
    dimnames = dimnames - set(ds_to.dimensions.keys())
    dimnames = sorted(dimnames)
    if do_debug:
        print 'Dim names: ', dimnames

    attrnames = set(ds_from.ncattrs())
    if include_attrs:
        attrnames = attrnames & set(include_attrs)
    elif exclude_attrs:
        attrnames = attrnames - set(exclude_attrs)
    attrnames = attrnames - set(ds_to.ncattrs())
    attrnames = sorted(attrnames)
    if do_debug:
        print 'Global attr names: ', attrnames

    # copy attributes
    for attrname in attrnames:
        attr_val = ds_from.getncattr(attrname)
        ds_to.setncattr(attrname, attr_val)
        if do_debug:
            print 'Set global attr "{}" = {}'.format(attrname,  attr_val)

    # copy dimensions
    for dimname in dimnames:
        dim = ds_from.dimensions[dimname]
        if dim.isunlimited():
            dim_len = None
        else:
            dim_len = len(dim)
        ds_to.createDimension(dimname, size=dim_len)
        if do_debug:
            print 'Set dim "{}" * {}'.format(dimname,  dim_len)

    # copy variables, their attributes and values
    for varname in varnames:
        var = ds_from.variables[varname]
        # remove fill_value from attrs for special handling via CreateVariable
        attrnames = var.ncattrs()
        magic_fv_name = '_FillValue'
        if magic_fv_name in attrnames:
            fill_value = var.getncattr(magic_fv_name)
            attrnames.remove(magic_fv_name)
        else:
            fill_value = None
        if do_debug:
            print 'Make var "{}"[{}] : {}'.format(
                varname,  var.dimensions, var.dtype)
        # create the variable
        outvar = ds_to.createVariable(varname, var.dtype, var.dimensions,
                                      fill_value=fill_value)
        # set variable attributes
        for attrname in attrnames:
            attr_val = var.getncattr(attrname)
            if do_debug:
                print '  attr "{}" = {}'.format(attrname, attr_val)
            outvar.setncattr(attrname, attr_val)
        # set variable values
        if do_debug:
            print '  vars[{}] = ...'.format(outvar.shape)
        outvar[:] = var[:]

if __name__ == '__main__':
    # get openDAP url from usercode e.g.
    # - in : /net/home/h05/itpp/Remedy/opendap_merge_WO0000000053538/work/load_opendap.py
    a = 'http://nomads.ncdc.noaa.gov/thredds/dodsC/narrmonthly/'
    b = 'narrmon-a_221_'
    c = '_0000_000.grb'
    fstring = "{0}{1}{2:02d}/{1}{2:02d}{3:02d}/{4}{1}{2:02d}{3:02d}{5}"
    years = range(1988,1990)
    months = range(1,12,4)
    d = 1 # because its monthly averaged
    narr_opendap = [fstring.format(a, y, m, d, b, c) for y in years for m in months ]

    # open this dataset 
    ds = netCDF4.Dataset(narr_opendap[0])

    # copy it to temporary in my homespace
    ds2 = netCDF4.Dataset('/home/h05/itpp/tmp.nc', 'w')
    nc_copy(ds, ds2,
            include_vars=['Temperature_surface', 'time1', 'Lambert_Conformal', 'x', 'y'],
            exclude_attrs=['file_format'])
    ds2.close()
    print
    print 'Done ok.'
