ncobj
=====

A Python object representation of NetCDF4 data, allowing more flexible
programmatic handling of NetCDF files.
Enables quick+easy copying of data from one netCDF4 file to another, with
arbitrary changes.  Intended scope similar to NCO commands.

Latest web docs : http://pp-mo.github.io/build/html/ncobj.html

Current Status
--------------
VERSION "0.1.1" : 2014-04-17
 * Core classes written
   * Basic unit tests written + working.
   * Some integration tests, currently disabled.
 * Structure management prototype code (ncobj.grouping)
   * Unit tests written, and working.
   * Integration tests wanted.
 * Basic file i/o working (ncobj.nc_dataset)
   * some simple tests
 * Documentation with Sphinx
 * Non-working usecase examples demonstrate intended coding forms + api.

Further motivation and ideas :
------------------------------
 * It should be possible to copy data (variables etc) from one file to another.
   * we are solving this by defining how to recreate missing dims etc.
 * a deferred access for variables data should certainly be available
 * ultimately, this should include the ability to performed streamed operations on files larger than the memory
   * e.g. see https://github.com/SciTools/biggus
 * a straightforward read-modify-write will not be efficient for making simple
changes to existing files (which the existing NetCDF4 does perfectly well).
Should be able to compare content with an existing file and optimise,
especially when the variables data already exists in the output file (as
visible from variables' deferred data representation).
