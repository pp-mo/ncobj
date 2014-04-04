ncobj
=====

A Python object representation of NetCDF4 data, allowing more flexible
programmatic handling of NetCDF files.
Enables quick+easy copying of data from one netCDF4 file to another, with
arbitrary changes.  Intended scope similar to NCO commands.

Present Status
--------------
2014-04-04:
 *  Still reworking core classes + writing tests.
 * Some unit tests written + working.
 * No working file i/o yet.

Further motivation and ideas :
------------------------------
 * It should be possible to copy data (variables etc) from one file to another.
   * we are solving this by defining how to recreate missing dims etc.
 * a deferred access for variables data should certainly be available
 * ultimately, this should include the ability to performed streamed operations on files larger than the memory
   * e.g. https://github.com/SciTools/biggus
   
