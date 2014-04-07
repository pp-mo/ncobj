"""
Sample code for usecases of interest.
NOTE: not functional, just demonstrating how API concepts might work.

"""

import datetime
import glob
import os.path

import iris.Unit  # just for the calendar processing...

import ncobj as nco
from ncobj import Attribute, Variable, Dimension, Group
import ncobj.grouping as ncg
import ncobj.nc_dataset as nc_files


def EG_prune_dimensions(group):
        dims_used = []
        for var in ncg.all_variables(group):
            dims_used += var.dimensions
        for dim in ncg.all_contents_oftype(group, Dimension):
            if dim not in dims_used:
                dim.remove()


def EG_filter_variables():
    # Filter variables, removing some, and flatten structure.
    input_path = os.path.join(basedir, 'test.nc')
    output_path = os.path.join(basedir, 'test_out.nc')
    # Read input.
    input = nc_files.read(input_path)
    # Make blank output.
    output = Group()
    varname_parts_only = ('temp', 'depth')
    varname_ends_exclude = ('_QC', '_stats')
    # Copy selected variables.
    for var in ncg.all_variables(input):
        if (any(var.name.find(part) >= 0 for part in varname_parts_only) and
            not any(var.name.find(part) >= 0 for part in varname_ends_not)):
                output.variables.add(var)
    # Write out.
    nc_files.write(output_path)


def EG_extract_combine():
    # Combine selected data with a month's worth each from several files.

    input_paths = glob.glob(os.path.join(basedir, 'test_sequence_*.nc'))
    output_path = os.path.join(basedir, 'test_out.nc')
    desired_var_names = ('air_temperature', 'surface_pressure')

    # Create a suitable empty output structure.
    output = Group()
    output.dimensions.add(Dimension('time', length=0))
    output_time_dim = output.dimensions['time']
    output.variables.add(Variable('time', dimensions=output_time_dim))
    output_time_var = output.variables['time']
    # N.B. time 'units' attribute and data array added later, copied from
    # the first input file.

    # sort input filenames for correct data times ordering
    input_paths = sorted(input_paths)

    # get whole months from input files in name order and concat to output.
    first_file = True
    for input_path in input_paths:
        input = nc_files.read(input_path)

        # Get input file time information.
        time_var = input.variables['time']
        time_units = time_var.attributes['units'].value
        time_dts = iris.Unit(time_units).num2date(time_var[:])
        monthdays = np.array([dt.day for dt in time_dts])

        if first_file:
            first_file = False
            # First time through, establish time base at first month start.
            time_next = time_dts[np.where(monthdays == 1)[0][0]]

            # First time though, initialise time variable units + data (empty).
            output_time_var.attributes.add(
                Attribute(name='units', value=time_units))
            output_time_var.data = np.array([])

            # First time through, create output variables matching input.
            for varname in desired_var_names:
                output.variables[varname] = input.variables[varname]
                var = output.variables[varname]
                assert var.dimensions[0].name == 'time'
                # Change first dimension to output_time (current length=0).
                var.dimensions[0] = output_time_var
                dim_lens = [dim.length for dim in var_dims]
                assert dim_lens[0] == 0
                # Assign a data array of correct dimensions (initially empty).
                var.data = np.array(dim_lens)

        # Get index for the month start.
        month_start = np.where(time_dts == time_next)[0][0]
        # Calculate next start date.
        is_december = time_next.month == 12
        time_next = datetime.datetime(
            year=year+1 if is_december else year,
            month=1 if is_december else month+1,
            day=1)
        # Get index for the month end, or -1 if not in file.
        next_months = np.where(time_dts == time_next)[0]
        month_end = next_months[0] if next_months else -1

        # Slice a month from the desired variables and copy to the output.
        for varname in desired_var_names:
            var = input.variables[varname]
            assert var.dimensions[0].name == 'time'
            # Note: this array concatenation is crude + expensive in memory.
            # This is where we really need deferred data management.
            output.variables[varname].data = np.concatenate(
                (output.variables[varname][:], var[month_start:month_end]),
                axis=0)
            #
            # NOTE: a cool one-line version, that may not be possible ...
            #     output.variables[varname][-1:] = var[month_start:month_end]
            # (N.B. you can do this with lists, but *not* numpy arrays)
            #

        # Extend the time coord variable appropriately.
        # NOTE: with missing data, the time values sequence will show gaps.
        output_time_var.data = np.concatenate(
            (output_time_var[:], time_var[month_start:month_end]), axis=0)

    # Write the output file.
    nc_files.write(output)
