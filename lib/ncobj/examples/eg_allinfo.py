"""
Code to create a netcdf4 file with "all" possible features for CDL testing.
(Supported features, that is).

"""
import netCDF4 as nc4
import numpy as np
import os

import ncobj.grouping as ncg
from ncobj.shorts import og, od, ov, oa
import ncobj.nc_dataset as ncf

g = og(
    'rootname',
    aa=[oa('root_attr_num', 1),
        oa('root_attr_str', 'xyz'),
        oa('root_attr_vec', np.array([1.2, 3, 4]))],
    dd=[od('root_dim_x', 2)],
    vv=[ov('root_var_1',
           dd=[od('root_dim_x')],
           aa=[oa('root_var_attr_1', 11)],
           data=np.zeros((2))),
        ov('root_var_2_scalar', data=np.array(3.15, dtype=np.float32))],
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
print(g)
print()
file_path = './temp.nc'
with nc4.Dataset(file_path, 'w') as ds:
    ncf.write(ds, g)
print()
os.system('ncdump -h temp.nc')
