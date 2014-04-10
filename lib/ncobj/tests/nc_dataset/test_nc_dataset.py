import unittest as tests


import ncobj.nc_dataset as ncd


class Test_nc_dataset(tests.TestCase):
    def test_basic_load(self):
        test_path = '/data/local/dataZoo/netCDF/global/xyt/total_column_co2.nc'
        ds = ncd.read(test_path)
        self.assertIs(ds.variables['tcco2'].dimensions[1],
                      ds.dimensions['latitude'])


if __name__ == '__main__':
    tests.main()
