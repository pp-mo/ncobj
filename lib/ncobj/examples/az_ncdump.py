#!/usr/bin/env python2.7
'''
Produce ncdump, but with all elements in alphabetical order.

NOTE: creation / handle order does exist in netCDF4, somewhat hidden ...
    dim._dimid, var._varid, <group or var>.ncattrs()-order

We could support that later, if we want.

'''
import argparse
import netCDF4
import ncobj.nc_dataset as ncds
import ncobj.cdl as ncdl


# ncdl._DEBUG_CDL = True


def ncfile_cdl(file_path):
    with netCDF4.Dataset(file_path) as ds:
        group = ncds.read(ds)
        result = ncdl.group_cdl(group)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Produce standard-order CDL from netCDF files.')
    parser.add_argument('input',
                        metavar='INPUT',
                        help='Path to netCDF file')
    args = parser.parse_args()
    print ncfile_cdl(args.input)
