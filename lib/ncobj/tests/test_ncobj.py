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

    def test_container__unwritable(self):
        with self.assertRaises(AttributeError):
            self.nco.container = 'newname'

    def test_rename__isolated(self):
        self.nco.rename('newname')
        self.assertEqual(self.nco.name, 'newname')

    def test_container__contained(self):
        self.assertEqual(self.nco_contained.container, self.mock_container)

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
        self.mock_container.pop.assert_called_once_with(
            self.nco_contained, None)
        # NOTE: nco.container is *not* reset -- the container does that.


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


class TestDimension(tests.TestCase, GenericNcObjTestMixin):
    def setUp(self):
        self.test_element = ncobj.Dimension(name='test', length=5)
        self.test_el_unlimited = ncobj.Dimension(name='test')

    def test_length__unlimited(self):
        self.assertIsNone(self.test_el_unlimited.length)

    def test_length__finite(self):
        self.assertEqual(self.test_element.length, 5)

    def test_length__unwriteable(self):
        with self.assertRaises(AttributeError):
            self.test_element.length = 2

    def test_isunlimited__unlimited(self):
        self.assertTrue(self.test_el_unlimited.isunlimited())

    def test_isunlimited__finite(self):
        self.assertFalse(self.test_element.isunlimited())


class TestAttribute(tests.TestCase, GenericNcObjTestMixin):
    def setUp(self):
        self.test_element = ncobj.Attribute(name='test', value='val')

    def test_value(self):
        self.assertEqual(self.test_element.value, 'val')

    def test_value__unwriteable(self):
        with self.assertRaises(AttributeError):
            self.test_element.value = 2


class TestVariable(tests.TestCase, GenericNcObjTestMixin):
    def setUp(self):
        self.test_element = ncobj.Variable(name='test')


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
                                  type=float,
                                  data=[[1, 2, 3], [4, 5, 6]])
            var1.attributes.add(ncobj.Attribute('var_att_a', value='this'))
            self.nco.variables.add(var1)
            var2 = ncobj.Variable('var_B',
                                  dimensions=(),
                                  type=float,
                                  data=[])
            self.nco.variables.add(var2)
            print
            print self.nco

    #    def test_all(self):
    #        nco = NcFile(self.input_dataset)
    #        nco.write()

        def test_exclude_vars(self):
            for var in self.nco.all_variables():
                print
                print var
                if var.name in ('exc_1', 'exc_2'):
                    var.remove()
            print
            print 'new result:'
            print '\n'.join(str(x) for x in self.nco.treewalk_content())
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


if __name__ == '__main__':
    tests.main()
