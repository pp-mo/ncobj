import  unittest as tests

import ncobj

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
        var1 = ncobj.Variable('var_x',
                 dimensions=(dim_y, dim_x),
                 dtype=float,
                 data=[[1, 2, 3], [4, 5, 6]])
        var1.attributes.add(ncobj.Attribute('var_att_a', value='this'))
        self.nco.variables.add(var1)

#    def test_all(self):
#        nco = NcFile(self.input_dataset)
#        nco.write()

    def test_exclude_vars(self):
        for var in self.nco.all_variables():
            if var.name in ('exc_1', 'exc_2'):
                var.remove()
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
