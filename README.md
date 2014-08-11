ncobj
=====

A Python object representation of NetCDF4 data, allowing more flexible
programmatic handling of NetCDF files.
Enables quick+easy copying of data from one netCDF4 file to another, with
arbitrary changes.  Intended scope similar to NCO commands.

Latest web docs : http://pp-mo.github.io/build/html/index.html

Current Status
--------------
VERSION "0.3" : 2014-08-12
 * Core classes written and full unit tests.
 * File i/o via netCDF4 (ncobj.nc_dataset)
   * some simple tests
 * CDL generation facility for ncobj elements.
 * Documentation with Sphinx
 * Working examples:
   * generate netcdf file from scratch
   * 'semantic containers' manipulations
   * alphabetic-ordered CDL dumps
 * Non-working usecase examples demonstrate intended coding forms + api.

