"""
Read and check operation on all NetCDF files in the Iris-test-data subdirectory
'NetCDF/testing'.

In each case, check we can read and write the data, and produce CDL output
basically similar to the 'ncdump' output.

"""
import glob
import os.path
import subprocess

from iris.tests import get_data_path as iris_testdata_path
import netCDF4
import ncobj.nc_dataset as ncds
import ncobj.cdl as ncdl
from ncobj.cdl import cdl


def check_file_cdl(file_path):
    # Load from the given file
    with netCDF4.Dataset(file_path) as ds:
        g = ncds.read(ds)
        # Re-save to a temporary file, to get an ncdump output in known order.
        ncds.write('temp.nc', g)
        # Rename so name matches temporary file name as seen by ncdump.
        g.rename('temp')
        # Generate cdl.
        g_cdl = cdl(g)
    try:
        # Run ncdump on the test file
        f_cdl = subprocess.check_output('ncdump -h temp.nc', shell=True)
    finally:
        os.remove('temp.nc')
    # Check that the two CDL strings are "essentially" the same.
    g_cdl_std = ncdl.comparable_cdl(g_cdl)
    f_cdl_std = ncdl.comparable_cdl(f_cdl)
    if g_cdl_std == f_cdl_std:
        print('OK    (ncdump and ncobj output EQUAL)')
    else:
        print('FAIL: ncdump and ncobj output differ..')
    print()


testfiles_dirpath = iris_testdata_path(('NetCDF', 'testing'))
testfiles_pathspec = os.path.join(testfiles_dirpath, '*.nc')
file_paths = glob.glob(testfiles_pathspec)
for file_path in file_paths:
    print()
    print('FILE {}:'.format(file_path))
    check_file_cdl(file_path)

print()
print('--DONE--')
