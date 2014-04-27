import unittest as tests

try:
    import netCDF4 as nc4
    _nc4_available = True
except ImportError:
    _nc4_available = False

import numpy as np

import ncobj.cdl as ncdl
import ncobj.grouping as ncg
from ncobj.shorts import og, od, ov, oa


def print_linewise_diffs(id1, id2, str1, str2):
    for il, (l1, l2) in enumerate(zip(str1.split('\n'), str2.split('\n'))):
        if l1 != l2:
            print ' {:>10s} #{:04d}:  {}'.format(id1, il, l1)
            print '  {:>10s}#{:04d}:  {}'.format(id2, il, l2)


# Define a complex test group.
# NOTE: this also wants 'completing', which is a bit heavy for import code,
# so do that during testcode instead.
def _make_complex_group():
    g = og(
        'temp',
        aa=[oa('a_root_attr_num', 1),
            oa('q_root_attr_str', 'xyz'),
            oa('b_root_attr_vec', np.array([1.2, 3, 4])),
            oa('z_root_attr_num', 1),
            oa('c_root_attr_str', 'xyz'),
            oa('l_root_attr_vec', np.array([1.2, 3, 4])),
            oa('d_root_attr_num', 1),
            oa('f_root_attr_str', 'xyz'),
            oa('n_root_attr_vec', np.array([1.2, 3, 4]))],
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
                      aa=[oa('subgroup_var_attr', 57.31)],
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
_complex_cdl = """
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
        :d_root_attr_num = 1L ;
        :f_root_attr_str = "xyz" ;
        :l_root_attr_vec = 1.2, 3., 4. ;
        :n_root_attr_vec = 1.2, 3., 4. ;
        :q_root_attr_str = "xyz" ;
        :z_root_attr_num = 1L ;

    group: sg_2_empty {
    } // group sg_2_empty
    group: subgroup {

    dimensions:
        subgroup_dim_y = 3 ;

    variables:
        double subgroup_var(root_dim_x, subgroup_dim_y) ;
                subgroup_var:subgroup_var_attr = 57.31 ;

    // group attributes:
        :subgroup_attr = "qq" ;

        group: sub_sub_group {

        variables:
            double sub_sub_group_var(subgroup_dim_y) ;

        // group attributes:
            :sub_sub_group_attr = "this" ;
        } // group sub_sub_group
    } // group subgroup
    }
    """


class Test_cdl(tests.TestCase):
    def test_comparable_cdl__basic(self):
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
        result_str = ncdl.comparable_cdl(test_str)
        if result_str != expected_str:
            # (Debug output)
            print 'results do not match:'
            print_linewise_diffs('result', 'expected',
                                 result_str, expected_str)
        self.assertEqual(result_str, expected_str)

    def test_cdl(self):
        g = _make_complex_group()
        result_cdl = ncdl.group_cdl(g)
        expect_cdl = _complex_cdl[:]
        # Compare, but skipping comments and whitespace.
        result_cmp = ncdl.comparable_cdl(result_cdl)
        expect_cmp = ncdl.comparable_cdl(expect_cdl)
        if result_cmp != expect_cmp:
            # (Debug output)
            print_linewise_diffs('group_cdl output', 'expected',
                                 result_cmp, expect_cmp)
        self.assertEqual(result_cmp, expect_cmp)


if _nc4_available:
    import ncobj.nc_dataset as ncf
    import os.path
    import shutil
    import subprocess
    import tempfile

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

            def strip_lines(string):
                lines = string.split('\n')
                lines = [line.strip() for line in lines]
                lines = [line for line in lines if len(line)]
                return '\n'.join(lines)

            expected = strip_lines(ncdump_output)
            found = strip_lines(results)
            if expected != found:
                # (Debug output)
                print_linewise_diffs('expected', 'got', expected, found)
            self.assertEqual(found, expected)


if __name__ == '__main__':
    tests.main()
