ncobj
=====

A Python object representation of NetCDF4 data, allowing more flexible
programmatic handling of NetCDF files.
Enables quick+easy copying of data from one netCDF4 file to another, with
arbitrary changes.  Intended scope similar to NCO commands.

Status
------
2014-04-15:
 * Core classes written
   * Basic unit tests written + working.
   * Some integration tests, currently disabled.
 * Structure management prototype code (ncobj.grouping)
   * Partial unit tests written, and working.
   * Still more to write.
 * Non-working usecase examples demonstrate intended coding forms + api.
 * No working file i/o yet.


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
