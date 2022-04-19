#!/usr/bin/env python2.7
'''
Example script to make modified copies of NetCDF files, changing some details
that we needed to fix.

'''
import argparse
import datetime
import netCDF4
import numpy as np

import ncobj.nc_dataset as ncds


# Define a common reference time for our reconstructed time coordinates.
basetime_units_string = 'days since 1970-01-01'
basetime_dt = datetime.datetime(1970, 1, 1)


def copy_and_fix_file(infile_path, outfile_path):
    with netCDF4.Dataset(infile_path) as ds_in:
        g = ncds.read(ds_in)
        result = tweak_data(g)
        with netCDF4.Dataset(outfile_path, 'w') as ds_out:
            ncds.write(ds_out, result)


def tweak_data(g):
    # Remove 'history' and 'Creationdate' attributes, which vary by file and so
    # prevent merging in Iris.
    g.attributes['history'].remove()
    g.attributes['Creationdate'].remove()

    # Remove the non-standard 'date' attribute and convert it back into an
    # actual time value.
    # (Values are like E.G. "20100430_day")
    date = g.attributes.pop('Date')
    date_string = date.value
    date_string, tail = date_string.split('_')
    assert tail == 'day'
    # get date from string : **N.B. this assumes the gregorian calendar**
    date_dt = datetime.datetime.strptime(date_string, "%Y%m%d")
    # Convert 'date' to days since a specific common basetime.
    time_value = (date_dt - basetime_dt).total_seconds()
    time_value /= (3600.0 * 24)

    # Check the existing 'time' coord has the expected properties ...
    var_time = g.variables['time']
    # Expect one 'time' dimension.
    assert len(var_time.dimensions) == 1
    assert var_time.dimensions[0].name == 'time'
    # Expect only one value.
    assert var_time.data.shape == (1,)
    # Expect it to already have a 'units' attribute (which we will change).
    assert 'units' in var_time.attributes.names()

    # Remove the time 'bounds' attribute...
    bnds_attr = var_time.attributes.pop('bounds')
    # ...Because the variable referred to is absent (check this).
    expect_bnds_name = 'time_bnds'
    assert bnds_attr.value == expect_bnds_name
    assert expect_bnds_name not in g.variables.names()

    # Reset the time to the value extracted from the 'Date' attribute.
    var_time.data = np.array([time_value])
    var_time.attributes['units'].value = basetime_units_string

    # Remove comment attribute, which is no longer valid.
    comment_attr = var_time.attributes.pop('comment')
    assert 'date is set to the 15th' in comment_attr.value

    return g


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Make a CF-adjusted version of a COSP NetCDF4 file.')
    parser.add_argument('infile_path', metavar='INPUT',
                        help='Path to input netCDF file')
    parser.add_argument('outfile_path', metavar='OUTPUT', nargs='?',
                        help='Path to output netCDF file')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Print details of operation')
    args = parser.parse_args()
    infile_path, outfile_path = args.infile_path, args.outfile_path
    if outfile_path is None:
        outfile_path = infile_path + '.cf'
    if args.verbose:
        print('COSP adjusting : {} --> {}'.format(infile_path, outfile_path))
    copy_and_fix_file(infile_path, outfile_path)
