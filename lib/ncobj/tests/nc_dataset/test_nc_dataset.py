import unittest as tests


try:
    import netCDF4 as nc4
    _nc4_available = True
except ImportError:
    _nc4_available = False

import numpy as np
import os
import os.path


import ncobj.grouping as ncg
from ncobj.shorts import og, od, ov, oa

if _nc4_available:
    from ncobj.nc_dataset import read, write


_here_dirpath = os.path.dirname(__file__)
_testdata_relpath = './testdata'
testdata_dirpath = os.path.abspath(os.path.join(_here_dirpath,
                                                _testdata_relpath))

leave_output = False


@tests.skip(not _nc4_available)
class Test_read(tests.TestCase):
    def test_simple(self):
        test_filename = 'units.nc'
        test_filepath = os.path.join(testdata_dirpath, test_filename)
        with netCDF4.Dataset(test_filepath) as ds:
            g = read(ds)
            self.assertIs(g.variables['cube_0'].dimensions[0],
                          g.dimensions['time'])


@tests.skip(not _nc4_available)
class Test_write(tests.TestCase):
    def test_simple_to_path(self):
        test_outfile_name = 'test_simple.nc'
        test_outfile_path = os.path.join(testdata_dirpath,
                                         test_outfile_name)
        array = np.arange(4)
        var = ov('v1', dd=[od('x')], aa=[oa('v_att', 'this')], data=array)
        g = og('', vv=[var])
        self.assertFalse(ncg.has_no_missing_dims(g))
        try:
            write(test_outfile_path, g)
            self.assertTrue(ncg.has_no_missing_dims(g))
            # Read it back again and check.
            with netCDF4.Dataset(test_outfile_path) as ds:
                g_back = read(ds)
                self.assertEqual(g_back, g)
        finally:
            if not leave_output:
                # Remove temporary file
                if os.path.exists(test_outfile_path):
                    os.remove(test_outfile_path)

    def test_add_to_dataset(self):
        test_outfile_name = 'test_add.nc'
        test_outfile_path = os.path.join(testdata_dirpath, test_outfile_name)
        try:
            ds = netCDF4.Dataset(test_outfile_path, 'w')
            ds.setncattr('extra', 4.5)
            g = og('', vv=[ov('v1', aa=[oa('var_attr', 'this_value')],
                              data=np.array(3.2))])
            write(ds, g)
            ds.close()
            # Read it back again and check.
            with netCDF4.Dataset(test_outfile_path) as ds:
                g = read(ds)
                self.assertEqual(g.attributes['extra'].value, 4.5)
                self.assertEqual(list(g.dimensions), [])
                self.assertEqual(
                    g.variables['v1'].attributes['var_attr'].value,
                    'this_value')
        finally:
            if not leave_output:
                if os.path.exists(test_outfile_path):
                    os.remove(test_outfile_path)


if __name__ == '__main__':
    tests.main()
