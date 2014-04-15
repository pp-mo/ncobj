import unittest as tests


import ncobj as nco

from ncobj.grouping import walk_group_objects
from ncobj.grouping import all_variables, all_dimensions, all_groups
from ncobj.grouping import group_path
from ncobj.grouping import find_named_definition as fnd
from ncobj.grouping import NameConflictError, DimensionConflictError
from ncobj.grouping import check_group_name_clashes as check_names
from ncobj.grouping import _has_varsdata as group_is_tagged
from ncobj.grouping import _add_dims_varsdata as tag_group
from ncobj.grouping import check_dims_usage_consistent as check_dims


class _BaseTest_Grouping(tests.TestCase):
    def check_all_in_str(self, str, matches):
        for match in matches:
            self.assertIn(match, str)


def og(name, aa=None, dd=None, vv=None, gg=None):
    return nco.Group(name,
                     dimensions=dd,
                     variables=vv,
                     attributes=aa,
                     sub_groups=gg)


def oa(name, v=None):
    return nco.Attribute(name, value=v)


def od(name, l=None, u=False):
    return nco.Dimension(name, length=l, unlimited=u)


def ov(name, dd=None, aa=None):
    return nco.Variable(name, dimensions=dd, attributes=aa,
                        dtype=None, data=[])


class Test_walk_group_objects(_BaseTest_Grouping):
    def setUp(self):
        self.root = og('',
                       aa=[oa('test_global_attr', v='test string')],
                       dd=[od('t', 3)],
                       vv=[ov('x')],
                       gg=[og('group_X',
                              dd=[od('x', 3), od('y', 2)],
                              vv=[ov('var_A', dd=[od('y'), od('x')],
                                     aa=[oa('var_att_a', 'this')]),
                                  ov('var_B', dd=[od('t')])],
                              aa=[oa('att_1', 4.3), oa('att_2', 4.7)])])
        subgroup = self.root.groups['group_X']
        self.all_objs = [
            self.root,
            self.root.attributes['test_global_attr'],
            self.root.dimensions['t'],
            self.root.variables['x'],
            subgroup,
            subgroup.attributes['att_1'],
            subgroup.attributes['att_2'],
            subgroup.dimensions['x'],
            subgroup.dimensions['y'],
            subgroup.variables['var_A'],
            subgroup.variables['var_B']]

    def test_basic(self):
        walk_objs = list(walk_group_objects(self.root))
        # NOTE: can't use set-equality here, as it test 'is' not '__eq__'.
        for elem in self.all_objs:
            self.assertIn(elem, walk_objs)
        for obj in walk_objs:
            self.assertIn(obj, self.all_objs)

    def _check_all_of_type(self, walk_objs, elem_type):
        for elem in self.all_objs:
            if isinstance(elem, elem_type):
                self.assertIn(elem, walk_objs)
            else:
                self.assertNotIn(elem, walk_objs)
        for obj in walk_objs:
            self.assertIsInstance(obj, elem_type)
            self.assertIn(obj, self.all_objs)

    def test_all_variables(self):
        walk_objs = list(all_variables(self.root))
        self._check_all_of_type(walk_objs, nco.Variable)

    def test_all_dimensions(self):
        walk_objs = list(all_dimensions(self.root))
        self._check_all_of_type(walk_objs, nco.Dimension)

    def test_all_groups(self):
        walk_objs = list(all_groups(self.root))
        self._check_all_of_type(walk_objs, nco.Group)


class Test_group_path(_BaseTest_Grouping):
    def test_isolate_and_attribute(self):
        self.assertEqual('att_a', group_path(oa('att_a')))

    def test_root_and_variable(self):
        g = og('', vv=[ov('var_test_xx')])
        test_var = g.variables['var_test_xx']
        self.assertEqual('/var_test_xx',
                         group_path(test_var))

    def test_subgroup_and_dimension(self):
        g = og('', gg=[og('sub_group', dd=[od('dim_q')])])
        test_dim = g.groups['sub_group'].dimensions['dim_q']
        self.assertEqual('/sub_group/dim_q',
                         group_path(test_dim))


class Test_find_named_definition(_BaseTest_Grouping):
    def test_type_bad(self):
        g = og('')
        with self.assertRaises(ValueError) as err_context:
            fnd(g, 'name', type(None))
        msg = err_context.exception.message
        self.check_all_in_str(msg, ['<type \'NoneType\'>',
                                    'not recognised',
                                    'or not supported'])

    def test_type_unsupported(self):
        g = og('')
        with self.assertRaises(ValueError) as err_context:
            fnd(g, 'name', nco.Variable)
        msg = err_context.exception.message
        self.check_all_in_str(msg, ['ncobj.Variable',
                                    'not recognised',
                                    'or not supported'])

    def test_root_none(self):
        g = og('')
        self.assertIsNone(fnd(g, 'dim_q', nco.Dimension))

    def test_root_in(self):
        g = og('', dd=[od('dim_q', 2)])
        test_dim = g.dimensions['dim_q']
        self.assertIs(fnd(g, 'dim_q', nco.Dimension),
                      test_dim)

    def test_root_notin(self):
        g = og('', dd=[od('dim_q_NOT', 2)])
        self.assertIsNone(fnd(g, 'dim_q', nco.Dimension))

    def test_subgroup_none(self):
        g = og('', gg=[og('sg')])
        test_grp = g.groups['sg']
        self.assertIsNone(fnd(test_grp, 'dim_q', nco.Dimension))

    def test_subgroup_notin(self):
        g = og('', gg=[og('sg', dd=[od('dim_q', 3)])])
        test_grp = g.groups['sg']
        self.assertIsNone(fnd(test_grp, 'dim_q_NOT', nco.Dimension))

    def test_subgroup_in(self):
        g = og('', gg=[og('sg', dd=[od('dim_q', 3)])])
        test_grp = g.groups['sg']
        test_dim = test_grp.dimensions['dim_q']
        self.assertEquals(fnd(test_grp, 'dim_q', nco.Dimension),
                          test_dim)

    def test_subgroup_in_parent(self):
        g = og('', gg=[og('sg')], dd=[od('dim_q', 3)])
        test_grp = g.groups['sg']
        test_dim = g.dimensions['dim_q']
        self.assertEquals(fnd(test_grp, 'dim_q', nco.Dimension),
                          test_dim)


class Test_check_group_name_clashes(_BaseTest_Grouping):
    def test_empty(self):
        g = og('root')
        self.assertFalse(group_is_tagged(g))
        check_names(g)
        self.assertFalse(group_is_tagged(g))

    def test_okay(self):
        g = og('root', vv=[ov('test_v')], dd=[od('test_d')],
               gg=[og('test_g')])
        self.assertFalse(group_is_tagged(g))
        check_names(g)
        self.assertFalse(group_is_tagged(g))

    def test_var_vs_dim(self):
        g = og('root', vv=[ov('tst1')], dd=[od('tst1')])
        with self.assertRaises(NameConflictError) as err_context:
            check_names(g)
        msg = err_context.exception.message
        self.check_all_in_str(msg, ['group "root"', 'both',
                                    'variable', 'dimension', 'tst1'])

    def test_var_vs_grp(self):
        g = og('root', vv=[ov('tst1')], gg=[og('tst1')])
        with self.assertRaises(NameConflictError) as err_context:
            check_names(g)
        msg = err_context.exception.message
        self.check_all_in_str(msg, ['group "root"', 'both',
                                    'variable', 'group', 'tst1'])

    def test_dim_vs_grp(self):
        g = og('root', dd=[od('tst1')], gg=[og('tst1')])
        with self.assertRaises(NameConflictError) as err_context:
            check_names(g)
        msg = err_context.exception.message
        self.check_all_in_str(msg, ['group "root"', 'both',
                                    'dimension', 'group', 'tst1'])

    def test_subgroup_okay(self):
        g = og('root', vv=[ov('test_var')],
               gg=[og('tst1', vv=[ov('test_var')])])
        subgroup = g.groups['tst1']
        self.assertFalse(group_is_tagged(g))
        self.assertFalse(group_is_tagged(subgroup))
        check_names(g)
        self.assertFalse(group_is_tagged(g))
        self.assertFalse(group_is_tagged(subgroup))


class Test_check_dims_usage_consistent(_BaseTest_Grouping):
    def test_empty(self):
        g = og('')
        check_dims(g)

    def test_okay_single(self):
        g = og('', dd=[od('x')], vv=[ov('v1', dd=[od('x')])])
        check_dims(g)

    def test_okay_match(self):
        g = og('', dd=[od('x')],
               vv=[ov('v1', dd=[od('x', 3)]),
                   ov('v2', dd=[od('x', 3)])])
        check_dims(g)

    def test_fail_nomatch(self):
        g = og('', dd=[od('x')],
               vv=[ov('v1', dd=[od('x', 2)]),
                   ov('v2', dd=[od('x', 3)])])
        with self.assertRaises(DimensionConflictError) as err_context:
            check_dims(g)
        msg = err_context.exception.message
        self.check_all_in_str(msg, ['/v1', '"x" = 2', '/v2', '"x" = 3'])

    def test_okay_match_unlimited(self):
        g = og('', dd=[od('x')],
               vv=[ov('v1', dd=[od('x', 3)]),
                   ov('v2', dd=[od('x', 3, u=True)])])
        check_dims(g)

    def test_okay_match_subgroup(self):
        g = og('', dd=[od('x')],
               vv=[ov('v1', dd=[od('x', 2)])],
               gg=[og('subgroup', vv=[ov('v2', dd=[od('x', 2)])])])
        check_dims(g)

    def test_fail_nomatch_subgroup(self):
        g = og('', dd=[od('x')],
               vv=[ov('v1', dd=[od('x', 2)])],
               gg=[og('subgroup', vv=[ov('v2', dd=[od('x', 3)])])])
        with self.assertRaises(DimensionConflictError) as err_context:
            check_dims(g)
        msg = err_context.exception.message
        self.check_all_in_str(msg, ['/v1', '"x" = 2',
                                    '/subgroup/v2', '"x" = 3'])

    def test_okay_override_subgroup(self):
        # NOTE: here *two* 'x' dimensions, which do not conflict.
        g = og('', dd=[od('x')],
               vv=[ov('v1', dd=[od('x', 2)])],
               gg=[og('subgroup',
                      dd=[od('x')],
                      vv=[ov('v2', dd=[od('x', 3)])])])
        check_dims(g)

    def test_with_varsdata_okay(self):
        g = og('', dd=[od('x')],
               vv=[ov('v1', dd=[od('x', 2)])],
               gg=[og('subgroup', vv=[ov('v2', dd=[od('x', 2)])])])
        subgroup = g.groups['subgroup']
        tag_group(g)
        self.assertTrue(group_is_tagged(g))
        self.assertFalse(group_is_tagged(subgroup))
        check_dims(g)
        self.assertTrue(group_is_tagged(g))
        self.assertFalse(group_is_tagged(subgroup))

    def test_with_varsdata_fail(self):
        g = og('', dd=[od('x')],
               vv=[ov('v1', dd=[od('x', 2)])],
               gg=[og('subgroup', vv=[ov('v2', dd=[od('x', 3)])])])
        subgroup = g.groups['subgroup']
        tag_group(g)
        self.assertTrue(group_is_tagged(g))
        self.assertFalse(group_is_tagged(subgroup))
        with self.assertRaises(DimensionConflictError):
            check_dims(g)
        self.assertTrue(group_is_tagged(g))
        self.assertFalse(group_is_tagged(subgroup))


if __name__ == '__main__':
    tests.main()
