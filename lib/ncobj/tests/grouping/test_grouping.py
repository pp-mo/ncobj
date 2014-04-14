import unittest as tests


import ncobj as nco

from ncobj.grouping import \
    walk_group_objects, all_variables, all_dimensions, all_groups, \
    group_path


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

        
class Test_walk_group_objects(MixinTestSetup):
    def test_basic(self):
        walk_objs = list(walk_group_objects(self.root))
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
    def test_isolate(self):
        self.assertEqual(group_path(self.attr_sub_var_A_A), 'var_att_a')

    def test_root(self):
        self.assertEqual(group_path(self.root.variables['x']), '/x')

    def test_subgroup(self):
        self.assertEqual(group_path(self.subgroup.dimensions['x']),
                         '/group_X/x')


if __name__ == '__main__':
    tests.main()
