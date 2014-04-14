import unittest as tests

import mock
import ncobj


class Test_NcObj(tests.TestCase):
    def setUp(self):
        self.compares_eq = mock.sentinel._is_eq
        self.compares_neq = mock.sentinel._not_eq
        _match_val = self.compares_eq

        class MyObj(ncobj.NcObj):
            def __eq__(self, other):
                # Test argument as surrogate for compare.
                return other == _match_val

            def detached_copy(self):
                # (Abstract method requires a definition).
                pass

        self.nco = MyObj('myname')
        self.mock_container = mock.Mock(spec=ncobj.NcobjContainer)
        self.nco_contained = MyObj('myname')
        self.nco_contained._container = self.mock_container

    def test_name(self):
        self.assertEqual(self.nco.name, 'myname')

    def test_name__unwritable(self):
        with self.assertRaises(AttributeError):
            self.nco.name = 'newname'

    def test_container__isolated(self):
        self.assertIsNone(self.nco.container)

    def test_container__contained(self):
        self.assertEqual(self.nco_contained.container, self.mock_container)

    def test_container__unwritable(self):
        with self.assertRaises(AttributeError):
            self.nco.container = 'newname'

    def test_is_definition__isolated(self):
        self.assertFalse(self.nco.is_definition())

    def test_is_definition__contained(self):
        testval = mock.sentinel.isdef_retval
        self.mock_container.is_definitions = mock.Mock(return_value=testval)
        self.assertEqual(self.nco_contained.is_definition(), testval)

    def test_rename__isolated(self):
        self.nco.rename('newname')
        self.assertEqual(self.nco.name, 'newname')

    def test_rename__contained(self):
        self.nco_contained.rename('newname')
        self.mock_container.rename_element.assert_called_once__with(
            'newname')

    def test___ne__iseq(self):
        self.assertEqual(self.nco != self.compares_eq, False)

    def test___ne__noteq(self):
        self.assertEqual(self.nco != self.compares_neq, True)

    def test_remove(self):
        self.nco_contained.remove()
        self.mock_container.remove.assert_called_once_with(self.nco_contained)
        # NOTE: nco.container is *not* reset in this test
        #  -- that is done in the implementation of the real container.


class GenericNcObjTestMixin(object):
    """Simple functional tests to perform on all derived NcObj types."""
    def test_detached_copy__detached(self):
        test_el = self.test_element
        copy_el = test_el.detached_copy()
        self.assertIsNot(copy_el, test_el)
        self.assertEqual(copy_el, test_el)

    def test_detached_copy__attached(self):
        test_el = self.test_element
        test_el._container = mock.Mock(spec=ncobj.NcobjContainer)
        copy_el = test_el.detached_copy()
        self.assertIsNot(copy_el, test_el)
        self.assertEqual(copy_el, test_el)
        self.assertIsNotNone(test_el._container)
        self.assertIsNone(copy_el._container)

    def test__eq__(self):
        el = self.test_element
        el_eq = el.detached_copy()
        el_ne = el.detached_copy()
        el_ne.rename('q')
        self.assertTrue(el == el)
        self.assertTrue(el == el_eq)
        self.assertFalse(el == el_ne)

    def test__ne__(self):
        el = self.test_element
        el_eq = el.detached_copy()
        el_ne = el.detached_copy()
        el_ne.rename('q')
        self.assertFalse(el != el)
        self.assertFalse(el != el_eq)
        self.assertTrue(el != el_ne)


class Test_Dimension(tests.TestCase, GenericNcObjTestMixin):
    def setUp(self):
        self.test_element = ncobj.Dimension(name='test', length=5)
#        self.test_el_unlimited = ncobj.Dimension(name='test', unlimited=True)

#    def test_length__unlimited(self):
#        self.assertIsNone(self.test_el_unlimited.length)
#
#    def test_length__finite(self):
#        self.assertEqual(self.test_element.length, 5)
#
#    def test_length__writeable(self):
#        self.test_element.length = 2
#        self.assertEqual(self.test_element.length, 2)
#
#    def test_isunlimited__unlimited(self):
#        self.assertTrue(self.test_el_unlimited.unlimited)
#
#    def test_isunlimited__finite(self):
#        self.assertFalse(self.test_element.unlimited)
#
#    # TODO: unlimited + length now decoupled + independent
#    # needs more tests ?


class Test_Attribute(tests.TestCase, GenericNcObjTestMixin):
    def setUp(self):
        self.test_element = ncobj.Attribute(name='test', value='val')

    def test_value(self):
        self.assertEqual(self.test_element.value, 'val')

    def test_value__write(self):
        # Freely rewritable for now, no typing.
        self.test_element.value = 2
        self.assertEqual(self.test_element.value, 2)
        self.test_element.value = 'yes'
        self.assertEqual(self.test_element.value, 'yes')


class Test_Variable(tests.TestCase, GenericNcObjTestMixin):
    def setUp(self):
        self.test_element = ncobj.Variable(name='test')


class Test_NcobjContainer(tests.TestCase):
    def setUp(self):
        class TestNcObj(ncobj.NcObj):
            def detached_copy(self):
                return TestNcObj(self.name)

            def __eq__(self, other):
                return self.name == other.name

        class TestContainer(ncobj.NcobjContainer):
            @property
            def element_type(self):
                return TestNcObj

# This way tests a specific type + its container.
# Only Variable or Group can actually be created with just a name arg.
#        TestNcObj = ncobj.Variable
#        TestContainer = ncobj.NcVariablesContainer

        self.con = TestContainer()
        self.parent_group = mock.Mock(spec=ncobj.Group)
        self.con_ingroup = TestContainer(in_element=self.parent_group)

        self.content_a = TestNcObj('A')
        self.content_b = TestNcObj('B')
        self.content_c = TestNcObj('C')
        self.con_nonempty = TestContainer([self.content_a, self.content_b])
        self.con_nonempty_ingroup = TestContainer(
            [self.content_a, self.content_b],
            in_element=self.parent_group)

    def test_in_element__none(self):
        self.assertIsNone(self.con.in_element)

    def test_in_element__ingroup(self):
        self.assertEqual(self.con_ingroup.in_element, self.parent_group)

    def test_in_element__unwriteable(self):
        with self.assertRaises(AttributeError):
            self.con.in_element = self.parent_group

    def test_isdefinitions__none(self):
        self.assertFalse(self.con.is_definitions())

    def test_isdefinitions__ingroup(self):
        self.assertTrue(self.con_ingroup.is_definitions())

    def test_names__empty(self):
        self.assertEqual(self.con.names(), [])

    def test_names__nonempty(self):
        names = self.con_nonempty.names()
        self.assertEqual(sorted(names), ['A', 'B'])

    def test_detached_contents_copy__empty(self):
        result = self.con.detached_contents_copy()
        self.assertIsNot(result, self.con)
        self.assertEqual(result, self.con)

    def test_detached_contents_copy__nonempty(self):
        result = self.con_nonempty.detached_contents_copy()
        self.assertIsNot(result, self.con_nonempty)
        self.assertEqual(result, self.con_nonempty)
        self.assertEqual(result.names(), self.con_nonempty.names())
        for name in result.names():
            self.assertEqual(result[name], self.con_nonempty[name])
            self.assertIsNot(result[name], self.con_nonempty[name])

    def test_detached_contents_copy__nonempty_ingroup(self):
        result = self.con_nonempty_ingroup.detached_contents_copy()
        self.assertIsNot(result, self.con_nonempty_ingroup)
        self.assertEqual(result, self.con_nonempty_ingroup)
        self.assertEqual(self.con_nonempty_ingroup.in_element,
                         self.parent_group)
        self.assertEqual(result.in_element, None)

    def test___getitem___(self):
        self.assertEqual(self.con_nonempty['A'], self.content_a)
        with self.assertRaises(KeyError):
            _ = self.con['ZZZ']

    def test__setitem__(self):
        with self.assertRaises(KeyError):
            _ = self.con['A']
        self.con['A'] = self.content_a
        con_a = self.con['A']
        self.assertEqual(con_a, self.content_a)
        self.assertIsNot(con_a, self.content_a)
        self.assertEqual(con_a.container, self.con)
        self.assertIsNone(self.content_a.container)

    def test__setitem__rename(self):
        self.assertNotEqual(self.content_a.name, 'Z')
        self.assertTrue('Z' not in self.con.names())
        self.con['Z'] = self.content_a
        self.assertNotEqual(self.content_a.name, 'Z')
        self.assertTrue('Z' in self.con.names())

    def test__setitem__badtype(self):
        class TestNcObjAlternative(ncobj.NcObj):
            pass
        with self.assertRaises(TypeError):
            self.con['any'] = TestNcObjAlternative('A')

    def test__setitem__badname(self):
        with self.assertRaises(ValueError):
            self.con[1] = self.content_a
        with self.assertRaises(ValueError):
            self.con[''] = self.content_a

    def test__setitem__nameclash(self):
        self.assertTrue(self.content_a not in self.con)
        self.con['A'] = self.content_a
        self.assertTrue(self.content_a in self.con)
        with self.assertRaises(ValueError):
            self.con['A'] = self.content_a

    def test_get__empty(self):
        self.assertIsNone(self.con.get('A'))
        tempdef = mock.sentinel.con_get_default
        self.assertEqual(self.con.get('A', tempdef), tempdef)

    def test_get__nonempty(self):
        con_a = self.con_nonempty.get('A')
        self.assertEqual(con_a, self.content_a)
        self.assertIn(con_a, self.con_nonempty)
        self.assertEqual(self.con_nonempty.get('Z'), None)
        tempdef = mock.sentinel.con_get_default
        self.assertEqual(self.con.get('Z', tempdef), tempdef)

    def test_pop(self):
        with self.assertRaises(KeyError):
            _ = self.con.pop('A')
        con_a = self.con_nonempty['A']
        self.assertEqual(con_a.container, self.con_nonempty)
        self.assertIn(con_a, self.con_nonempty)
        result = self.con_nonempty.pop('A')
        self.assertEqual(sorted(self.con_nonempty.names()), ['B'])
        self.assertIs(result, con_a)
        self.assertNotIn(con_a, self.con_nonempty)
        self.assertIsNone(con_a.container)

    def test__delitem__(self):
        with self.assertRaises(KeyError):
            del self.con['A']
        del self.con_nonempty['B']
        self.assertEqual(sorted(self.con_nonempty.names()), ['A'])

    def test_remove(self):
        with self.assertRaises(KeyError) as err_context:
            _ = self.con.remove(self.content_a)
        self.assertEqual(err_context.exception.args, (self.content_a,))
        result = self.con_nonempty.pop('A')
        self.assertEqual(result, self.content_a)
        self.assertEqual(sorted(self.con_nonempty.names()), ['B'])

    def test_add(self):
        self.con.add(self.content_a)
        self.assertIn(self.content_a, self.con)
        with self.assertRaises(ValueError):
            self.con.add(self.content_a)

    def test__iter__(self):
        with self.assertRaises(StopIteration):
            _ = iter(self.con).next()
        self.assertEqual(iter(self.con_nonempty).next(), self.content_a)
        self.assertTrue(self.content_a not in self.con)
        self.assertTrue(self.content_a in self.con_nonempty)
        self.assertTrue(list(self.con_nonempty),
                        [self.content_a, self.content_b])

    def test_len(self):
        self.assertEqual(len(self.con), 0)
        self.assertEqual(len(self.con_nonempty), 2)

    def test_rename_element(self):
        con_a = self.con_nonempty['A']
        self.con_nonempty.rename_element(con_a, 'Q')
        self.assertEqual(self.con_nonempty['Q'], con_a)
        self.assertEqual(con_a.name, 'Q')
        self.assertEqual(con_a.container, self.con_nonempty)
        self.assertEqual(sorted(self.con_nonempty.names()), ['B', 'Q'])


class Test_Group(tests.TestCase, GenericNcObjTestMixin):
    def setUp(self):
        self.test_element = ncobj.Group()

    def parent_group__orphan(self):
        self.assertIsNone(self.test_element.parent_group)

    def parent_group__child(self):
        parent = self.test_element
        child = ncobj.Group('child_name', parent_group=parent)
        self.assertEqual(child.parent_group, parent)

if 0:
    class Test__api(tests.TestCase):    
        def setUp(self):
    #        self.input_dataset = object()

            self.nco = ncobj.Group()
            att1 = ncobj.Attribute('att_1', value=4.3)
            att2 = ncobj.Attribute('att_2', value=4.7)
            self.nco.attributes.add(att1)
            self.nco.attributes.add(att2)
            dim_y = ncobj.Dimension('y', length=2)
            dim_x = ncobj.Dimension('x', length=3)
            self.nco.dimensions.add(dim_x)
            self.nco.dimensions.add(dim_y)
            var1 = ncobj.Variable('var_A',
                                  dimensions=(dim_y, dim_x),
                                  dtype=float,
                                  data=[[1, 2, 3], [4, 5, 6]])
            var1.attributes.add(ncobj.Attribute('var_att_a', value='this'))
            self.nco.variables.add(var1)
            var2 = ncobj.Variable('var_B',
                                  dimensions=(),
                                  dtype=float,
                                  data=[])
            self.nco.variables.add(var2)
            print
            print self.nco

    #    def test_all(self):
    #        nco = NcFile(self.input_dataset)
    #        nco.write()

        def test_exclude_vars(self):
            import ncobj.grouping as og
            for var in og.walk_group_objects(self.nco, ncobj.Variable):
                print
                print var
                if var.name in ('exc_1', 'exc_2'):
                    var.remove()
            print
            print 'new result:'
            print '\n'.join(str(x) for x in og.walk_group_objects(self.nco))
    #        self.nco.write(self.out_file)

    #    def test_strip_varattr(self):
    #        remove_att_name = 'remove_att'
    #        for var in nco.all_variables():
    #            var.pop(remove_att_name, None)
    #        nco.write(self.out_file)
    #
    #    def test_remove_dim(self):
    #        remove_dim_name = 'remove_x1_dim'
    #        var = nco.variables['x']
    #        data = var.data[indices]
    #        dims = var.dimensions.copy()
    #        dims.remove(remove_dim_name)
    #        data = data.reshape([dim.length for dim in dims])
    #        var2 = ncobj.NcVariable(name=var.name,
    #                                dtype=var.dtype,
    #                                dimensions=dims,
    #                                data=data,
    #                                attributes=var.attributes)
    #        del nco.dimensions[remove_dim_name]
    #        nco.write(sel.out_file)
    #
    #
    #    def test_tweak_units(self):
    #        units_from = 'Pa'
    #        units_to = 'Kg m-1 s2'
    #        unit_attname = 'units'
    #        for var in nco.all_variables():
    #            units_att = var.attributes.get(unit_attname)
    #            if units_att and units_att.value == units_from:
    #                units_att.value == units_to
    #        nco.write(sel.out_file)

if 1:
    class Test__complex(tests.TestCase):    
        def setUp(self):
            self.subgroup = ncobj.Group()
            att1 = ncobj.Attribute('att_1', value=4.3)
            att2 = ncobj.Attribute('att_2', value=4.7)
            self.subgroup.attributes.add(att1)
            self.subgroup.attributes.add(att2)
            dim_y = ncobj.Dimension('y', length=2)
            dim_x = ncobj.Dimension('x', length=3)
            self.subgroup.dimensions.add(dim_x)
            self.subgroup.dimensions.add(dim_y)
            var1 = ncobj.Variable('var_A',
                                  dimensions=(dim_y, dim_x),
                                  dtype=float,
                                  data=[[1, 2, 3], [4, 5, 6]])
            var1.attributes.add(ncobj.Attribute('var_att_a', value='this'))
            self.subgroup.variables.add(var1)
            var2 = ncobj.Variable('var_B',
                                  dimensions=(),
                                  dtype=float,
                                  data=[])
            self.subgroup.variables.add(var2)

            self.root = ncobj.Group()
            self.root.groups.setitem_reference('group_X', self.subgroup)

        def test__path(self):
            import ncobj.grouping as ncg
            print ncg.group_path(list(self.subgroup.variables)[0])

if __name__ == '__main__':
    tests.main()
