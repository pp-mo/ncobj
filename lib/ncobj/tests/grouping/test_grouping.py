import unittest as tests


import ncobj as nco

from ncobj.grouping import walk_group_objects
from ncobj.grouping import all_variables, all_dimensions, all_groups
from ncobj.grouping import group_path
from ncobj.grouping import find_named_definition as fnd


class MixinTestSetup(tests.TestCase):
    def setUp(self):
        self.subgroup = nco.Group()
        self.all_objs = [self.subgroup]
        self.sub_att_1 = nco.Attribute('att_1', value=4.3)
        self.sub_att_2 = nco.Attribute('att_2', value=4.7)
        self.subgroup.attributes.add(self.sub_att_1)
        self.subgroup.attributes.add(self.sub_att_2)
        self.all_objs += [self.sub_att_1, self.sub_att_2]
        self.dim_sub_y = nco.Dimension('y', length=2)
        self.dim_sub_x = nco.Dimension('x', length=3)
        self.subgroup.dimensions.add(self.dim_sub_x)
        self.subgroup.dimensions.add(self.dim_sub_y)
        self.all_objs += [self.dim_sub_x, self.dim_sub_y]
        self.var_sub_A = nco.Variable('var_A',
                                      dimensions=(self.dim_sub_y,
                                                  self.dim_sub_x),
                                      dtype=float,
                                      data=[[1, 2, 3], [4, 5, 6]])
        self.attr_sub_var_A_A = nco.Attribute('var_att_a', value='this')
        self.var_sub_A.attributes.add(self.attr_sub_var_A_A)
        self.subgroup.variables.add(self.var_sub_A)
        self.all_objs += [self.var_sub_A]
        # NO! : self.all_objs += [self.attr_sub_var_A_A]

        self.dim_sub_var_B_t = nco.Dimension('t', 5)
        self.var_sub_var_B = nco.Variable('var_B',
                                          dimensions=[self.dim_sub_var_B_t],
                                          dtype=float,
                                          data=[])
        self.subgroup.variables.add(self.var_sub_var_B)
        # NO! : self.all_objs += [self.dim_sub_var_B_t]
        self.all_objs += [self.var_sub_var_B]

        self.root = nco.Group()
        self.all_objs += [self.root]
        self.root.groups.setitem_reference('group_X', self.subgroup)
        self.attr_A = nco.Attribute('test_global_attr', 'test string')
        self.root.attributes['test_global_attr'] = self.attr_A
        self.all_objs += [self.attr_A]
        self.dim_T = nco.Dimension('t', 3)
        self.root.dimensions.add(self.dim_T)
        self.var_X = nco.Variable('x')
        self.root.variables.add(self.var_X)
        self.all_objs += [self.var_X, self.dim_T]


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


class Test__simple_maker(MixinTestSetup):
    # A quick test of our reduced-form structure builders
    def test__simple_maker(self):
        test_root = og('',
                       aa=[oa('test_global_attr', v='test string')],
                       dd=[od('t', 3)],
                       vv=[ov('x')],
                       gg=[og('group_X',
                              dd=[od('x', 3), od('y', 2)],
                              vv=[ov('var_A', dd=[od('y'), od('x')],
                                     aa=[oa('var_att_a', 'this')]),
                                  ov('var_B', dd=[od('t')])],
                              aa=[oa('att_1', 4.3), oa('att_2', 4.7)])])
#        print '\nTEST:\n', test_root
#        print '\nSELF:\n', self.root
        self.assertEqual(str(test_root), str(self.root))


class Test_walk_group_objects(MixinTestSetup):
    def test_basic(self):
        walk_objs = list(walk_group_objects(self.root))
        # NOTE: can't use set-equality here, as it test 'is' not '__eq__'.
        for elem in self.all_objs:
            self.assertIn(elem, walk_objs)
        for obj in walk_objs:
            self.assertIn(obj, walk_objs)

    def _check_all_of_type(self, walk_objs, elem_type):
        for elem in self.all_objs:
            if isinstance(elem, elem_type):
                self.assertIn(elem, walk_objs)
            else:
                self.assertNotIn(elem, walk_objs)
        for obj in walk_objs:
            self.assertIsInstance(obj, elem_type)
            self.assertIn(obj, walk_objs)

    def test_all_variables(self):
        walk_objs = list(all_variables(self.root))
        self._check_all_of_type(walk_objs, nco.Variable)

    def test_all_dimensions(self):
        walk_objs = list(all_dimensions(self.root))
        self._check_all_of_type(walk_objs, nco.Dimension)

    def test_all_groups(self):
        walk_objs = list(all_groups(self.root))
        self._check_all_of_type(walk_objs, nco.Group)


class Test_group_path(MixinTestSetup):
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


class Test_find_named_definition(MixinTestSetup):
    def check_all_in_str(self, str, matches):
        for match in matches:
            self.assertIn(match, str)

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


if __name__ == '__main__':
    tests.main()
