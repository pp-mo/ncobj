import unittest as tests

try:
    import netCDF4 as nc4
    _nc4_available = True
except ImportError:
    _nc4_available = False

import numpy as np

import ncobj.grouping as ncg
from ncobj.shorts import og, od, ov, oa

import ncobj.cdl as ncdl
from ncobj.cdl import cdl, comparable_cdl


# Define a complex test group.
# NOTE: this also wants 'completing', which is a bit heavy for import code,
# so do that during testcode instead.
def _make_complex_group():
    g = og(
        'temp',
        aa=[oa('a_root_attr_num', 1),
            oa('c_root_attr_str', 'xyz'),
            oa('b_root_attr_vec', np.array([1.2, 3, 4]))],
        dd=[od('root_dim_x', 2)],
        vv=[ov('root_var_1',
               dd=[od('root_dim_x')],
               aa=[oa('root_var_attr_1', 11)],
               data=np.zeros((2))),
            ov('root_var_2_scalar',
               data=np.array(3.15, dtype=np.float32))],
        gg=[og('subgroup',
               aa=[oa('subgroup_attr', 'qq')],
               dd=[od('subgroup_dim_y', 3)],
               vv=[ov('subgroup_var',
                      dd=[od('root_dim_x'), od('subgroup_dim_y')],
                      aa=[oa('subgroup_var_attr', 57.5)],
                      data=np.zeros((2, 3)))],
               gg=[og('sub_sub_group',
                      aa=[oa('sub_sub_group_attr', 'this')],
                      vv=[ov('sub_sub_group_var',
                             dd=[od('subgroup_dim_y')],
                             data=np.zeros((3)))])]),
            og('sg_2_empty')])
    ncg.complete(g)
    return g

# Define a CDL string matching the above.
_complex_cdl = """\
netcdf temp {

dimensions:
    root_dim_x = 2 ;

variables:
    double root_var_1(root_dim_x) ;
        root_var_1:root_var_attr_1 = 11L ;
    float root_var_2_scalar ;

// global attributes:
    :a_root_attr_num = 1L ;
    :b_root_attr_vec = 1.2, 3., 4. ;
    :c_root_attr_str = "xyz" ;

group: sg_2_empty {
} // group sg_2_empty

group: subgroup {

dimensions:
    subgroup_dim_y = 3 ;

variables:
    double subgroup_var(root_dim_x, subgroup_dim_y) ;
        subgroup_var:subgroup_var_attr = 57.5 ;

// group attributes:
    :subgroup_attr = "qq" ;
    
    group: sub_sub_group {
    
    variables:
        double sub_sub_group_var(subgroup_dim_y) ;
    
    // group attributes:
        :sub_sub_group_attr = "this" ;
    } // group sub_sub_group
} // group subgroup
}"""


class Test_comparable_cdl(tests.TestCase):
    def test__basic(self):
        test_str = """
            line1;  //no more
            line2 ;
            group {
                //this
                var =    expr(7  ** 5   /2)
                attributes:
                  :z = 3 ;
                  :a = 6 ;
                  :q = 4 ;
            }

            end"""
        expected_str = '\n'.join([
            "line1;",
            "line2 ;",
            "group {",
            "var = expr(7 ** 5 /2)",
            "attributes:",
            ":z = 3 ;",
            ":a = 6 ;",
            ":q = 4 ;",
            "}",
            "end"])
        result_str = comparable_cdl(test_str)
        self.assertEqual(result_str, expected_str)


class Test_cdl__attr(tests.TestCase):
    def test_scalar(self):
        result = cdl(oa('x', 3.21))
        self.assertEqual(result, 'x = 3.21')

    def test_array(self):
        result = cdl(oa('x', [3.21, 1.23]))
        self.assertEqual(result, 'x = 3.21, 1.23')

    def test_int(self):
        result = cdl(oa('x', 3))
        self.assertEqual(result, 'x = 3L')

    def test_string(self):
        result = cdl(oa('x', 'this'))
        self.assertEqual(result, 'x = "this"')

    def test_byte_type(self):
        result = cdl(oa('x', np.array(5, dtype=np.dtype('int8'))))
        self.assertEqual(result, 'x = 5b')

    def test_ubyte_type(self):
        result = cdl(oa('x', np.array(5, dtype=np.dtype('uint8'))))
        self.assertEqual(result, 'x = 5UB')

    def test_short_type(self):
        result = cdl(oa('x', np.array(5, dtype=np.dtype('int16'))))
        self.assertEqual(result, 'x = 5s')

    def test_ushort_type(self):
        result = cdl(oa('x', np.array(5, dtype=np.dtype('uint16'))))
        self.assertEqual(result, 'x = 5US')

    def test_single_type(self):
        result = cdl(oa('x', np.array(5, dtype=np.dtype('int32'))))
        self.assertEqual(result, 'x = 5')

    def test_unsigned_type(self):
        result = cdl(oa('x', np.array(5, dtype=np.dtype('uint32'))))
        self.assertEqual(result, 'x = 5U')

    def test_long_type(self):
        result = cdl(oa('x', np.array(5, dtype=np.dtype('int64'))))
        self.assertEqual(result, 'x = 5L')

    def test_ulong_type(self):
        result = cdl(oa('x', np.array(5, dtype=np.dtype('uint64'))))
        self.assertEqual(result, 'x = 5UL')

    def test_float_type(self):
        result = cdl(oa('x', np.array(1.23, dtype=np.dtype('float32'))))
        self.assertEqual(result, 'x = 1.23f')

    def test_double_type(self):
        result = cdl(oa('x', np.array(1.23, dtype=np.dtype('float64'))))
        self.assertEqual(result, 'x = 1.23')


class Test_cdl__dimension(tests.TestCase):
    def test_basic(self):
        result = cdl(od('x', 3))
        self.assertEqual(result, 'x = 3 ;')

    def test_unlimited(self):
        result = cdl(od('x', 3, u=True))
        self.assertEqual(result, 'x = UNLIMITED ;')


class Test_cdl__variable(tests.TestCase):
    def test_scalar(self):
        result = cdl(ov('x', data=np.array(3.21, dtype=np.float32)))
        self.assertEqual(result, 'float x ;')

    def test_1d(self):
        result = cdl(ov('x', dd=[od('p')], data=np.array(1.0)))
        self.assertEqual(result, 'double x(p) ;')

    def test_nd(self):
        result = cdl(ov('x', dd=[od('p'), od('q')], data=np.array(1.0)))
        self.assertEqual(result, 'double x(p, q) ;')

    def test_attrs(self):
        result = cdl(ov('x', dd=[od('p'), od('q')],
                        aa=[oa('n1', 3), oa('r1', 1.24)],
                        data=np.array(1.0)))
        self.assertEqual(result,
                         'double x(p, q) ;\n'
                         '    x:n1 = 3L ;\n'
                         '    x:r1 = 1.24 ;')

    def test_byte(self):
        result = cdl(ov('x', data=np.array(1, dtype=np.dtype('int8'))))
        self.assertEqual(result, 'byte x ;')

    def test_ubyte(self):
        result = cdl(ov('x', data=np.array(1, dtype=np.dtype('uint8'))))
        self.assertEqual(result, 'ubyte x ;')

    def test_short(self):
        result = cdl(ov('x', data=np.array(1, dtype=np.dtype('int16'))))
        self.assertEqual(result, 'short x ;')

    def test_ushort(self):
        result = cdl(ov('x', data=np.array(1, dtype=np.dtype('uint16'))))
        self.assertEqual(result, 'ushort x ;')

    def test_int(self):
        result = cdl(ov('x', data=np.array(1, dtype=np.dtype('int32'))))
        self.assertEqual(result, 'int x ;')

    def test_uint(self):
        result = cdl(ov('x', data=np.array(1, dtype=np.dtype('uint32'))))
        self.assertEqual(result, 'uint x ;')

    def test_long(self):
        result = cdl(ov('x', data=np.array(1, dtype=np.dtype('int64'))))
        self.assertEqual(result, 'int64 x ;')

    def test_ulong(self):
        result = cdl(ov('x', data=np.array(1, dtype=np.dtype('uint64'))))
        self.assertEqual(result, 'uint64 x ;')

    def test_float(self):
        result = cdl(ov('x', data=np.array(1.0,
                                           dtype=np.dtype('float32'))))
        self.assertEqual(result, 'float x ;')

    def test_double(self):
        result = cdl(ov('x', data=np.array(1.0)))
        self.assertEqual(result, 'double x ;')

    def test_chars(self):
        result = cdl(ov('x', dd=[od('STRLEN_4', 4)],
                        data=np.array(['t', 'h', 'i', 's'])))
        self.assertEqual(result, 'char x(STRLEN_4) ;')


class Test_cdl__group(tests.TestCase):
    def test__group(self):
        g = _make_complex_group()
        result_cdl = cdl(g)
        expect_cdl = _complex_cdl[:]
        self.assertEqual(result_cdl, expect_cdl)

    def test_empty(self):
        g = og('group_name')
        result = cdl(g)
        self.assertEqual(result, 'netcdf group_name {\n}')

    def test_attr(self):
        g = og('group_name', aa=[oa('x', 2)])
        result = cdl(g)
        self.assertEqual(result,
                         'netcdf group_name {\n'
                         '\n'
                         '// global attributes:\n'
                         '    :x = 2L ;\n'
                         '}')

    def test_dim(self):
        g = og('group_name', dd=[od('x', 2)])
        result = cdl(g)
        self.assertEqual(result,
                         'netcdf group_name {\n'
                         '\n'
                         'dimensions:\n'
                         '    x = 2 ;\n'
                         '}')

    def test_var(self):
        g = og('group_name', vv=[ov('x', data=np.array(1.0))])
        result = cdl(g)
        self.assertEqual(result,
                         'netcdf group_name {\n'
                         '\n'
                         'variables:\n'
                         '    double x ;\n'
                         '}')

    def test_inner_groups(self):
        g = og('group_name', gg=[og('sub_group')])
        result = cdl(g)
        self.assertEqual(result,
                         'netcdf group_name {\n'
                         '\n'
                         'group: sub_group {\n'
                         '} // group sub_group\n'
                         '}')

    def test_inner_group_attr(self):
        g = og('group_name',
               gg=[og('sub_group',
                      aa=[oa('x', 2)])])
        result = cdl(g)
        self.assertEqual(result,
                         'netcdf group_name {\n'
                         '\n'
                         'group: sub_group {\n'
                         '\n'
                         '// group attributes:\n'
                         '    :x = 2L ;\n'
                         '} // group sub_group\n'
                         '}')

    def test_inner_inner_group_attr(self):
        g = og('group_name',
               gg=[og('sub_group',
                      gg=[og('sub_sub_group',
                             aa=[oa('x', 2)])])])
        result = cdl(g)
        self.assertEqual(result,
                         'netcdf group_name {\n'
                         '\n'
                         'group: sub_group {\n'
                         '    \n'
                         '    group: sub_sub_group {\n'
                         '    \n'
                         '    // group attributes:\n'
                         '        :x = 2L ;\n'
                         '    } // group sub_sub_group\n'
                         '} // group sub_group\n'
                         '}')


if _nc4_available:
    import ncobj.nc_dataset as ncf
    import os.path
    import shutil
    import subprocess
    import tempfile

    def strip_lines(string):
        lines = string.split('\n')
        lines = [line.strip() for line in lines]
        lines = [line for line in lines if len(line)]
        return '\n'.join(lines)

    def sort_lines(string):
        lines = string.split('\n')
        return '\n'.join(sorted(lines))

    class Test_cdl__ncdump(tests.TestCase):
        def test_cdl__ncdump_match(self):
            ncdump_output = _complex_cdl[:]
            g = _make_complex_group()
            file_dirpath = tempfile.mkdtemp()
            try:
                file_path = os.path.join(file_dirpath, 'temp.nc')
                with nc4.Dataset(file_path, 'w') as ds:
                    ncf.write(ds, g)
                results = subprocess.check_output(
                    'ncdump -h ' + file_path, shell=True)
            finally:
                shutil.rmtree(file_dirpath)

            expected = strip_lines(ncdump_output)
            found = strip_lines(results)
            self.assertEqual(found, expected)

    class Test_cdl__alltypes(tests.TestCase):
        def _write_alltypes(self):
            pass

        def test_attrs(self):
            def _write_testdata(ds):
                # Create a simple x2 dimension for array testing.
                ds.createDimension('pair', 2)

                # Create variables + attributes of all netcdf basic types.
                for np_type, type_name in \
                        ncdl._DTYPES_TYPE_NAMES.iteritems():
                    if type_name == 'char':
                        scalar = 'A'
                        array = 'String_data'
                        # N.B. Wrapping this with np.array() has no effect.
                    else:
                        scalar = np.array(1.25, dtype=np_type)
                        array = np.array([1.25, 13.25], dtype=np_type)

                    attr_name = 'scalar_attr_' + type_name
                    ds.setncattr(attr_name, scalar)

                    attr_name = 'vector_attr_' + type_name
                    ds.setncattr(attr_name, array)

                    var_name = 'scalar_var_' + type_name
                    var = ds.createVariable(varname=var_name,
                                            datatype=np_type)
                    var[:] = scalar

                    var_name = 'array_var_' + type_name
                    var = ds.createVariable(varname=var_name,
                                            datatype=np_type,
                                            dimensions=('pair',))
                    var[:] = array

            testfile_name = 'alltypes.nc'
            temp_dirpath = tempfile.mkdtemp()
            try:
                file_path = os.path.join(temp_dirpath, testfile_name)
                with nc4.Dataset(file_path, 'w') as ds:
                    _write_testdata(ds)

                ncdump_output = subprocess.check_output(
                    'ncdump -h ' + file_path, shell=True)

                with nc4.Dataset(file_path, 'r') as ds:
                    read_data = ncf.read(ds)
                    read_data.rename('alltypes')
                    cdl_results = cdl(read_data)

                expected = sort_lines(strip_lines(ncdump_output))
                found = sort_lines(strip_lines(cdl_results))
                self.assertEqual(found, expected)

            finally:
                shutil.rmtree(temp_dirpath)


if __name__ == '__main__':
    tests.main()
