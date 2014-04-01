"""
Module for converting ncobj data to and from NetCDF Datasets.

"""

import netCDF4


import ncobj


class NcFile(ncobj.Group):
    def __init__(self, input_file=None, input_format=None):
        ncobj.Group.__init__(self)
        if input_file:
            if isinstance(input_file, netCDF4.Dataset):
                ds = input_file
            elif input_format:
                ds = netCDF4.Dataset(input_file, format=input_format)
            else:
                ds = netCDF4.Dataset(input_file)
            self.read(ds)

    def write(self, writable):
        pass

    def read(self, readable):
        # no groups yet, this is just ideas ...
        for attname in ds.ncattrs():
            value = ds.getncattr(attname)
            attribute = ncobj.Attribute(attname, value=value)
            ds.attributes.add(dimension)

        for (name, dim) in ds.dimensions.iteritems:
            length = None if dim.isunlimited() else len(dim)
            dimension = ncobj.Dimension(name, length=length)
            ds.dimensions.add(dimension)

        for (name, ds_var) in ds.variables.iteritems:
            dimensions = []
            for dim_name in ds_var.dimensions:
                ds_dim = ds.dimensions[dim_name]
                length = None if ds_dim.isunlimited() else len(ds_dim)
                dimensions.append(ncobj.Dimension(dim_name, length))
            attributes = []
            for attr_name in ds_var.ncattrs():
                value = ds_var.getncattr(attr_name)
                attributes.append(ncobj.Attribute(attr_name, value))
            variable = ncobj.Variable(name, group=self,
                                  dimensions=dimensions,
                                  dtype=ds_var.datatype,  # TODO user-types?
                                  data=ds_var,  # NOTE: so deferred!
                                  attributes=attributes)
            ds.variables.add(variable)

