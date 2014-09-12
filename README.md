ncobj
=====

A Python object representation of NetCDF4 data, allowing more flexible
programmatic handling of NetCDF files.  
Enables quick+easy copying of data from one netCDF4 file to another, with
arbitrary changes.  
Intended scope similar to NCO commands.

For example::

    import ncobj.nc_dataset as ncds
    with netCDF4.Dataset(file_in_path) as ds_in:
        in_group = ncds.read(ds_in)
        out_group = ncobj.Group()
        var = in_group.variables['my_temp']
        var.data = var.data[:100, 1::4]
        out_group.variables.add(var)
        ncds.write(file_out_path, out_group)

Latest web docs : http://pp-mo.github.io/build/html/index.html

Current Status
--------------
VERSION "0.3" : 2014-09-12
 * Core classes written and full unit tests.
 * File i/o via netCDF4 (ncobj.nc_dataset)
 * CDL generation facility for ncobj elements.
 * Documentation with Sphinx
 * Working examples:
   * generate netcdf file from scratch
   * subset all data by dimensions
   * alphabetic-ordered CDL dumps
   * 'semantic containers' manipulations
 * Non-working usecase examples demonstrate intended coding forms + api.

