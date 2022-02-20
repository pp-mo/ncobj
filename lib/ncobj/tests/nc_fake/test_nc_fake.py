"""
Unit tests for new "nc_fake" functionality.

All tests are applied to the fake objects are also exercised on real ones.

"""
import unittest as tests

try:
    import netCDF4 as nc
    _nc4_available = True
except ImportError:
    _nc4_available = False

import os
import os.path
import shutil
import tempfile

import numpy as np

import ncobj.nc_dataset
from ncobj.nc_fake import (DimensionMimic, VariableMimic, GroupMimic,
                           Nc4DatasetMimic, fake_nc4python_dataset)
from ncobj.shorts import og, od, ov, oa


class MixinNcFakeTest(object):
    def _make_temp_dataset(self):
        self._tempdir = tempfile.mkdtemp()
        self.ds = nc.Dataset(os.path.join(self._tempdir, 'tmp.nc'), 'w')

    def _destroy_temp_dataset(self):
        shutil.rmtree(self._tempdir)


class Test_DimensionMimic__bare(tests.TestCase, MixinNcFakeTest):
    def setUp(self):
        self._make_temp_dataset()

    def tearDown(self):
        self._destroy_temp_dataset()

    def test_dim_finite_with_length(self):
        nco_dim = od(name='dim2', l=3)
        fake_dim = self.ds.createDimension('dim2', 3)
        if _nc4_available:
            real_dim = DimensionMimic(nco_dim)
            test_dims = [real_dim, fake_dim]
        else:
            test_dims = [fake_dim]
        for dim in test_dims:
            self.assertEqual(dim.name, nco_dim.name)
            self.assertEqual(dim.isunlimited(), False)
            self.assertEqual(dim.size, 3)
            self.assertEqual(len(dim), 3)

    def test_dim_unlimited(self):
        # An ncobj.Dimension with no length, length 0, or unlimited=True,
        # all translate to 'length 0' dimension in netCDF4.
        nco_dim_bare = od(name='dim1')
        nco_dim_0_len = od(name='dim1', l=0)
        nco_dim_unlim_nolen = od(name='dim1', u=True)
        nco_dim_unlim_withlen = od(name='dim1', l=5, u=True)
        fake_dim_bare = DimensionMimic(nco_dim_bare)
        fake_dim_0_len = DimensionMimic(nco_dim_0_len)
        fake_dim_unlim_nolen = DimensionMimic(nco_dim_unlim_nolen)
        fake_dim_unlim_withlen = DimensionMimic(nco_dim_unlim_withlen)
        test_dims = [fake_dim_bare, fake_dim_0_len,
                fake_dim_unlim_nolen, fake_dim_unlim_withlen]
        if _nc4_available:
            real_dim = self.ds.createDimension('dim1', 0)
            test_dims = [real_dim] + test_dims
        for dim in test_dims:
            self.assertEqual(dim.name, 'dim1')
            self.assertEqual(dim.isunlimited(), True)
            self.assertEqual(len(dim), 0)
            self.assertEqual(dim.size, 0)


class Test_VariableMimic(tests.TestCase, MixinNcFakeTest):
    def setUp(self):
        self._make_temp_dataset()

    def tearDown(self):
        self._destroy_temp_dataset()

    def test_var_scalar(self):
        nco_var = ov(name='var1', data=np.array(1.2))
        fake_var = VariableMimic(nco_var)
        if _nc4_available:
            real_var = self.ds.createVariable('var1', float, ())
            real_var[:] = 1.2
            test_vars = [real_var, fake_var]
        else:
            test_vars = [fake_var]
        for var in test_vars:
            self.assertEqual(var.name, nco_var.name)
            self.assertEqual(var.dimensions, ())
            self.assertEqual(var.ndim, 0)
            self.assertEqual(var.shape, ())
            self.assertEqual(var.size, 1)
            self.assertEqual(var.dtype, np.float64)
            self.assertEqual(var.datatype, np.float64)
            data = var[:]
            self.assertEqual(data, 1.2)
            self.assertEqual(data.shape, ())

    def test_var_with_dims_and_data(self):
        xdim = od('x_dim', 3)
        ydim = od('y_dim', 2)
        data = np.array([[3, 1, 2], [4, 0, 7]])
        nco_var = ov(name='var1', dd=[ydim, xdim], data=data)
        fake_var = VariableMimic(nco_var)
        if _nc4_available:
            self.ds.createDimension('x_dim', 3)
            self.ds.createDimension('y_dim', 2)
            real_var = self.ds.createVariable('var1', int, ('y_dim', 'x_dim'))
            real_var[:] = data
            test_vars = [real_var, fake_var]
        else:
            test_vars = [fake_var]
        for var in test_vars:
            self.assertEqual(var.name, nco_var.name)
            self.assertEqual(var.dimensions, ('y_dim', 'x_dim'))
            self.assertEqual(var.ndim, 2)
            self.assertEqual(var.shape, (2, 3))
            self.assertEqual(var.size, 6)
            self.assertEqual(var.dtype, np.int64)
            self.assertEqual(var.datatype, np.int64)
            data = var[:]
            self.assertTrue(np.all(data == [[3, 1, 2], [4, 0, 7]]))
            self.assertEqual(data.shape, var.shape)

    def test_var_attrs_none(self):
        nco_var = ov(name='var1', dd=[od('x', 1)], data=12.3)
        fake_var = VariableMimic(nco_var)
        if _nc4_available:
            real_var = self.ds.createVariable('var1', float, ())
            test_vars = [real_var, fake_var]
        else:
            test_vars = [fake_var]
        for var in test_vars:
            self.assertEqual(var.ncattrs(), [])
            self.assertEqual(getattr(var, 'x', 'D-fault'), 'D-fault')
            with self.assertRaises(AttributeError):
                var.unknown
            with self.assertRaises(AttributeError):
                getattr(var, 'unknown')
            with self.assertRaises(AttributeError):
                var.getncattr('unknown')

    def test_var_attrs_some(self):
        nco_var = ov(name='var1', dd=[od('x', 1)], data=12.3,
                     aa=[oa('num', 3),
                         oa('text', 'string'),
                         oa('array', np.arange(2.0))])
        fake_var = VariableMimic(nco_var)
        if _nc4_available:
            real_var = self.ds.createVariable('var1', float, ())
            real_var.setncattr('num', 3)
            real_var.setncattr('text', 'string')
            real_var.setncattr('array', np.arange(2.0))
            test_vars = [real_var, fake_var]
        else:
            test_vars = [fake_var]
        for var in test_vars:
            self.assertEqual(sorted(var.ncattrs()), ['array', 'num', 'text'])
            self.assertEqual(getattr(var, 'x', 'D-fault'), 'D-fault')
            self.assertEqual(getattr(var, 'num', 'D-fault'), 3)
            self.assertEqual(var.num, 3)
            self.assertEqual(var.text, 'string')
            self.assertTrue(np.all(var.array == [0, 1]))


class Test_GroupMimic(tests.TestCase, MixinNcFakeTest):
    def setUp(self):
        self._make_temp_dataset()

    def tearDown(self):
        self._destroy_temp_dataset()

    def test_basic_group(self):
        ncobj_group = og('grp_A',
                         aa=[oa('att_x', 2), oa('att_y', 'xyz')],
                         dd=[od('y', 2), od('x', 3)],
                         vv=[ov('vx', dd=[od('x')],
                                data=np.array([1, 2, 3])),
                             ov('aa', dd=[od('y'), od('x')],
                                data=np.array([[1., 2, 3], [0, 0, 0]]))
                             ],
                         gg=[og('subgroup')])
        fake_group = GroupMimic(ncobj_group)
        if _nc4_available:
            whole_file_group = og('whole', gg=[ncobj_group])
            ncobj.nc_dataset.write(self.ds, whole_file_group)
            real_group = self.ds.groups['grp_A']
            test_groups = [fake_group, real_group]
        else:
            test_groups = [fake_group]
        for group in test_groups:
            self.assertEqual(group.name, 'grp_A')
            self.assertEqual(sorted(group.ncattrs()),
                             ['att_x', 'att_y'])
            self.assertEqual(sorted(group.dimensions),
                             ['x', 'y'])
            self.assertEqual(sorted(var.name
                                    for var in list(group.variables.values())),
                             ['aa', 'vx'])
            self.assertEqual(group.variables['aa'].dimensions, ('y', 'x'))
            self.assertEqual(len(group.groups), 1)
            self.assertEqual(group.groups['subgroup'].name, 'subgroup')


class Test_Nc4DatasetMimic(tests.TestCase):
    def test_dataset_mimic(self):
        # Just check it has a callable 'close' method.
        ncobj_group = og('group_X')
        fake_group = Nc4DatasetMimic(ncobj_group)
        fake_group.close()


class Test_nc4_python_dataset(tests.TestCase):
    def test_fake_dataset(self):
        # Just check that it returns something with properties like a dataset.
        ncobj_group = og('group_X')
        fake_file = fake_nc4python_dataset(ncobj_group)
        for prop_name in ('variables', 'dimensions', 'ncattrs', 'close'):
            self.assertTrue(hasattr(fake_file, prop_name))


if __name__ == '__main__':
    tests.main()
