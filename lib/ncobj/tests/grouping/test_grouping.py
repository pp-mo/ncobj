import unittest as tests


import mock
import ncobj as nco
from ncobj.shorts import og, od, ov, oa

from ncobj.grouping import walk_group_objects
from ncobj.grouping import all_variables, all_dimensions, all_groups
from ncobj.grouping import group_path
from ncobj.grouping import find_named_definition as fnd
from ncobj.grouping import NameConflictError, DimensionConflictError
from ncobj.grouping import IncompleteStructureError
from ncobj.grouping import check_group_name_clashes as check_names
from ncobj.grouping import _has_varsdata as group_is_tagged
from ncobj.grouping import _add_dims_varsdata as tag_group
from ncobj.grouping import check_consistent_dims_usage as check_dims
from ncobj.grouping import add_missing_dims
from ncobj.grouping import has_no_missing_dims
from ncobj.grouping import complete


class _BaseTest_Grouping(tests.TestCase):
    def check_all_in_str(self, string, matches):
        for match in matches:
            self.assertIn(match, string)


def _mockdata(shape):
    data = mock.Mock(spec=['shape'])
    data.shape = shape
    return data


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
            fnd(g, 'name', nco.Group)
        msg = err_context.exception.message
        self.check_all_in_str(msg, ['ncobj.Group',
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

    def test_var_vs_grp(self):
        g = og('root', vv=[ov('tst1')], gg=[og('tst1')])
        with self.assertRaises(NameConflictError) as err_context:
            check_names(g)
        msg = err_context.exception.message
        self.check_all_in_str(msg, ['group "root"', 'both',
                                    'variable', 'group', 'tst1'])

    def test_subgroup_okay(self):
        g = og('root', vv=[ov('test_var')],
               gg=[og('tst1', vv=[ov('test_var')])])
        subgroup = g.groups['tst1']
        self.assertFalse(group_is_tagged(g))
        self.assertFalse(group_is_tagged(subgroup))
        check_names(g)
        self.assertFalse(group_is_tagged(g))
        self.assertFalse(group_is_tagged(subgroup))


class Test_check_consistent_dims_usage(_BaseTest_Grouping):
    def test_empty(self):
        g = og('')
        check_dims(g)

    def test_single(self):
        g = og('', dd=[od('x')], vv=[ov('v1', dd=[od('x', 5)])])
        check_dims(g)

    def test_fail_nolength(self):
        g = og('', dd=[od('x')], vv=[ov('v1', dd=[od('x')])])
        with self.assertRaises(DimensionConflictError) as err_context:
            check_dims(g)
        msg = err_context.exception.message
        self.check_all_in_str(msg, ['No length', 'dimension "/x"'])

    def test_fail_incomplete(self):
        g = og('', vv=[ov('v1', dd=[od('x')])])
        with self.assertRaises(IncompleteStructureError):
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

    def test_with_data_shapes_okay(self):
        d1 = _mockdata((2, 3))
        var_xy = ov('v1_xy', dd=[od('x'), od('y')], data=d1)
        g = og('', dd=[od('x'), od('y')], vv=[var_xy])
        check_dims(g)

    def test_okay_data_shapes_override(self):
        d1 = _mockdata((2, 3))
        var_xy = ov('v1_xy', dd=[od('x'), od('y')], data=d1)
        g = og('', dd=[od('x', 17), od('y', 23)], vv=[var_xy])
        check_dims(g)

    def test_fail_conflicting_data_shapes(self):
        d1 = _mockdata((2, 23))
        v1 = ov('v1', dd=[od('x'), od('y')], data=d1)
        v2 = ov('v2', dd=[od('x', 17), od('y', 23)])
        g = og('', dd=[od('x'), od('y')], vv=[v1, v2])
        with self.assertRaises(DimensionConflictError) as err_context:
            check_dims(g)
        msg = err_context.exception.message
        self.check_all_in_str(msg, ['/v1', '/v2', '"x" = 17', '"x" = 2'])

    def test_fail_bad_data_shapes(self):
        d1 = _mockdata((5, 3, 2))
        g = og('', dd=[od('x'), od('y')],
               vv=[ov('v1', dd=[od('x'), od('y')], data=d1)])
        with self.assertRaises(DimensionConflictError) as err_context:
            check_dims(g)
        msg = err_context.exception.message
        self.check_all_in_str(msg, ['/v1', '3 dimensions', '2 dimensions'])


class Test_add_missing_dims(_BaseTest_Grouping):
    def test_empty(self):
        g = og('')
        add_missing_dims(g)

    def test_nomissing(self):
        g = og('', dd=[od('x')], vv=[ov('v', dd=[od('x')])])
        test_dim = g.dimensions['x']
        str_before = str(g)
        r = add_missing_dims(g)
        self.assertEqual(r, [])
        self.assertIs(g.dimensions['x'], test_dim)
        self.assertEqual(str(g), str_before)

    def test_missing(self):
        g = og('', vv=[ov('v', dd=[od('x')])])
        self.assertEqual(all_dimensions(g), [])
        r = add_missing_dims(g)
        self.assertEqual(r, [od('x')])
        self.assertEqual(all_dimensions(g), [od('x')])
        self.assertIs(g.dimensions['x'], r[0])

    def test_mixture(self):
        g = og('', dd=[od('x')], vv=[ov('v', dd=[od('y')])])
        self.assertEqual(all_dimensions(g), [od('x')])
        r = add_missing_dims(g)
        self.assertEqual(r, [od('y')])
        self.assertEqual(len(g.dimensions), 2)
        self.assertIs(r[0], g.dimensions['y'])

    def test_multiple(self):
        g = og('', vv=[ov('v1', dd=[od('x'), od('y')]),
                       ov('v2', dd=[od('y'), od('z')])])
        self.assertEqual(all_dimensions(g), [])
        r = add_missing_dims(g)
        self.assertEqual(len(r), 3)
        self.assertEqual(len(g.dimensions), 3)
        self.assertIn(od('x'), g.dimensions)
        self.assertIn(od('y'), g.dimensions)
        self.assertIn(od('z'), g.dimensions)

    def test_length(self):
        g = og('', vv=[ov('v', dd=[od('x', 2)])])
        self.assertEqual(all_dimensions(g), [])
        r = add_missing_dims(g)
        self.assertEqual(r, [od('x', 2)])
        self.assertEqual(len(g.dimensions), 1)
        self.assertNotEqual(all_dimensions(g), [od('x')])
        self.assertEqual(all_dimensions(g), [od('x', 2)])

    def test_unlimited(self):
        g = og('', vv=[ov('v', dd=[od('x', 2, u=True)])])
        self.assertEqual(all_dimensions(g), [])
        add_missing_dims(g)
        self.assertEqual(len(g.dimensions), 1)
        self.assertNotEqual(all_dimensions(g), [od('x', 2)])
        self.assertEqual(all_dimensions(g), [od('x', 2, u=True)])

    def test_shared_clash(self):
        # NOTE: "complete" won't allow this, but this method doesn't care.
        g = og('', vv=[ov('v1', dd=[od('x', 2)]),
                       ov('v2', dd=[od('x', 3)])])
        add_missing_dims(g)
        self.assertEqual(len(g.dimensions), 1)
        self.assertEqual(g.dimensions.names(), ['x'])

    def test_subgroup(self):
        g = og('',
               gg=[og('subgroup', vv=[ov('v1', dd=[od('y', 2)])])])
        add_missing_dims(g)
        self.assertEqual(len(g.dimensions), 1)
        self.assertEqual(g.dimensions.names(), ['y'])

    def test_subgroup_mixed(self):
        g = og('', vv=[ov('v1', dd=[od('q')])],
               gg=[og('subgroup', vv=[ov('v1', dd=[od('q', 2)])])])
        add_missing_dims(g)
        self.assertEqual(len(g.dimensions), 1)
        self.assertEqual(g.dimensions.names(), ['q'])


class Test_has_no_missing_dims(_BaseTest_Grouping):
    def test_empty(self):
        g = og('')
        self.assertTrue(has_no_missing_dims(g))

    def test_simple_fail(self):
        g = og('', vv=[ov('v', dd=[od('x')])])
        self.assertFalse(has_no_missing_dims(g))

    def test_fail_error(self):
        g = og('', vv=[ov('v', dd=[od('x')])])
        with self.assertRaises(IncompleteStructureError) as err_context:
            has_no_missing_dims(g, fail_if_not=True)
        msg = err_context.exception.message
        self.check_all_in_str(msg, [
            'Variable "/v"', 'dimension "x"', 'no definition exists'])

    def test_grouped_okay(self):
        g = og('', dd=[od('x'), od('y')],
               vv=[ov('v1', dd=[od('x')]), ov('v2', dd=[od('x'), od('y')])],
               gg=[og('subgroup', dd=[od('z')],
                      vv=[ov('sv1', dd=[od('x')]),
                          ov('sv2', dd=[od('y'), od('z')])])])
        self.assertTrue(has_no_missing_dims(g))

    def test_grouped_fail(self):
        g = og('', dd=[od('x'), od('y')],
               vv=[ov('v1', dd=[od('x')]), ov('v2', dd=[od('x'), od('y')])],
               gg=[og('subgroup', dd=[od('zz')],
                      vv=[ov('sv1', dd=[od('x')]),
                          ov('sv2', dd=[od('y'), od('z')])])])
        with self.assertRaises(IncompleteStructureError) as err_context:
            has_no_missing_dims(g, fail_if_not=True)
        msg = err_context.exception.message
        self.check_all_in_str(msg, [
            'Variable "/subgroup/sv2"', 'dimension "z"',
            'no definition exists'])


class Test_complete(_BaseTest_Grouping):
    def do_complete(self, group):
        # complete a group, and check that re-calling has no effect
#        print 'BEFORE:\n', group
        complete(group)
        self.assertTrue(has_no_missing_dims(group))
#        print 'FIRSTPASS:\n', group
        firstpass_result = group.detached_copy()
        complete(group)
#        print 'REDONE:\n', group
        self.assertEqual(group, firstpass_result)

    def test_empty(self):
        g = og('')
        self.do_complete(g)
        self.assertEqual(all_dimensions(g), [])

    def test_nomissing(self):
        g = og('',
               dd=[od('x', 3)],
               vv=[ov('v', dd=[od('x')])])
        test_dim = g.dimensions['x']
        self.assertEqual(all_dimensions(g), [test_dim])
        self.assertIsNot(g.variables['v'].dimensions[0], test_dim)
        self.do_complete(g)
        self.assertEqual(all_dimensions(g), [test_dim])
        self.assertIs(g.variables['v'].dimensions[0], test_dim)

    def test_missing(self):
        g = og('', vv=[ov('v', dd=[od('x', 7)])])
        self.assertEqual(all_dimensions(g), [])
        self.do_complete(g)
        self.assertEqual(all_dimensions(g), [od('x', 7)])
        self.assertIs(g.variables['v'].dimensions[0], g.dimensions['x'])

    def test_length_in_definition(self):
        g = og('',
               dd=[od('x', 7)],
               vv=[ov('v', dd=[od('x')])])
        x_def = g.dimensions['x']
        self.assertEqual(x_def, od('x', 7))
        self.assertEqual(all_dimensions(g), [x_def])
        self.assertIsNot(g.variables['v'].dimensions[0], x_def)
        self.do_complete(g)
        self.assertEqual(all_dimensions(g), [x_def])
        self.assertIs(g.variables['v'].dimensions[0], x_def)
        self.assertEqual(x_def, od('x', 7))

    def test_mixture(self):
        g = og('',
               dd=[od('x', 1)],
               vv=[ov('v', dd=[od('y', 3)])])
        self.assertEqual(all_dimensions(g), [od('x', 1)])
        self.do_complete(g)
        self.assertEqual(len(g.dimensions), 2)
        self.assertIn(od('x', 1), g.dimensions)
        self.assertIn(od('y', 3), g.dimensions)
        self.assertIs(g.variables['v'].dimensions[0], g.dimensions['y'])

    def test_multiple(self):
        g = og('', vv=[ov('v1', dd=[od('x', 1), od('y')]),
                       ov('v2', dd=[od('y', 2), od('z', 3)])])
        self.assertEqual(all_dimensions(g), [])
        self.do_complete(g)
        self.assertEqual(len(g.dimensions), 3)
        self.assertIn(od('x', 1), g.dimensions)
        self.assertIn(od('y', 2), g.dimensions)
        self.assertIn(od('z', 3), g.dimensions)
        v1, v2 = g.variables['v1'], g.variables['v2']
        dx, dy, dz = [g.dimensions[name] for name in ('x', 'y', 'z')]
        self.assertIs(v1.dimensions[0], dx)
        self.assertIs(v1.dimensions[1], dy)
        self.assertIs(v2.dimensions[0], dy)
        self.assertIs(v2.dimensions[1], dz)

    def test_length(self):
        g = og('', vv=[ov('v', dd=[od('x', 2)])])
        self.assertEqual(all_dimensions(g), [])
        self.do_complete(g)
        self.assertNotEqual(list(g.dimensions), [od('x')])
        self.assertEqual(list(g.dimensions), [od('x', 2)])

    def test_unlimited(self):
        g = og('', vv=[ov('v1', dd=[od('x', 2, u=True)]),
                       ov('v2', dd=[od('x', 2)])])
        self.assertEqual(all_dimensions(g), [])
        self.assertEqual(g.variables['v2'].dimensions[0], od('x', 2))
        self.do_complete(g)
        self.assertNotEqual(g.variables['v2'].dimensions[0], od('x', 2))
        self.assertEqual(list(g.dimensions), [od('x', 2, u=True)])
        test_dim = g.dimensions['x']
        self.assertIs(g.variables['v1'].dimensions[0], test_dim)
        self.assertIs(g.variables['v2'].dimensions[0], test_dim)

    def test_shared_clash_fail(self):
        g = og('', vv=[ov('v1', dd=[od('x', 2)]),
                       ov('v2', dd=[od('x', 3)])])
        with self.assertRaises(DimensionConflictError):
            self.do_complete(g)

    def test_subgroup(self):
        g = og('',
               gg=[og('subgroup', vv=[ov('v1', dd=[od('y', 2)])])])
        self.do_complete(g)
        self.assertEqual(len(g.dimensions), 1)
        self.assertEqual(list(g.dimensions), [od('y', 2)])
        self.assertIs(g.groups['subgroup'].variables['v1'].dimensions[0],
                      g.dimensions['y'])

    def test_subgroup_mixed(self):
        g = og('',
               vv=[ov('v1', dd=[od('q')])],
               gg=[og('subgroup',
                      vv=[ov('v1', dd=[od('q', 2)])])])
        self.assertEqual(list(g.dimensions), [])
        v1 = g.variables['v1']
        v2 = g.groups['subgroup'].variables['v1']
        self.do_complete(g)
        self.assertEqual(len(g.dimensions), 1)
        self.assertEqual(list(g.dimensions), [od('q', 2)])
        test_dim = g.dimensions['q']
        self.assertIs(v1.dimensions[0], test_dim)
        self.assertIs(v2.dimensions[0], test_dim)

    def test_part_complete(self):
        # Build a group with one variable already fixed to its dimension.
        g = og('',
               dd=[od('x', 3), od('q')],
               vv=[ov('v1')],
               gg=[og('subgroup', vv=[ov('v1', dd=[od('q', 2)])])])
        fixed_dim_x = g.dimensions['x']
        g.variables['v1'].dimensions = [fixed_dim_x]
        self.assertIs(g.variables['v1'].dimensions[0], fixed_dim_x)
        # Check that 'complete' fixes the other without rewriting this one.
        q_nolen = od('q')
        q_len = od('q', 2)
        var_dim_q = g.groups['subgroup'].variables['v1'].dimensions[0]
        grp_dim_q = g.dimensions['q']
        self.assertNotEqual(var_dim_q, grp_dim_q)
        self.assertEqual(var_dim_q, q_len)
        self.assertEqual(grp_dim_q, q_nolen)
        self.do_complete(g)
        self.assertIs(g.variables['v1'].dimensions[0], fixed_dim_x)
        var_dim_q = g.groups['subgroup'].variables['v1'].dimensions[0]
        grp_dim_q = g.dimensions['q']
        self.assertIs(var_dim_q, grp_dim_q)
        self.assertNotEqual(var_dim_q, q_nolen)
        self.assertEqual(var_dim_q, q_len)

    def test_simple_data(self):
        g = og('', vv=[ov('v', dd=[od('y'), od('x')],
                          data=_mockdata((15, 20)))])
        self.do_complete(g)
        self.assertEqual(len(g.dimensions), 2)
        self.assertEqual(g.dimensions['x'], od('x', 20))
        self.assertEqual(g.dimensions['y'], od('y', 15))


if __name__ == '__main__':
    tests.main()
