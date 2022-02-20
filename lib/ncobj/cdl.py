"""
Utility to produce CDL-style output for an :class:`ncobj.Element`.

Output is designed to be similar to "ncdump -h".  Variables data is completely
omitted.

Also includes a function to 'canonicalise' results for comparison with actual
ncdump output.

Extra notes:

 * Only ncobj supported features are managed (so currently no user-types).

 * Attributes containing vectors of strings are not handled, but at present
    netCDF4-python can not manage these anyway.

"""
import numpy as np


import ncobj as nco


def comparable_cdl(string):
    """
    Convert free-format (c code like) text into a 'canonical' form that can be
    directly compared.

    Replace all whitespace sequences with single spaces.
    Remove leading and trailing whitespace.
    Remove end-of-line comments.

    .. note::

        Currently does not ignore comments within quotes.

    """

    # Get individual lines
    lines = string.split('\n')

    # Remove rest-of-line comments
    # NOTE: strictly, this needs to ignore inside quotes
    def strip_rol_comment(string):
        index = string.find('//')
        return string if index < 0 else string[:index]

    lines = [strip_rol_comment(line) for line in lines]

    # Replace various whitespace with single characters
    # N.B. also compresses adjacent, and removes leading and trailing
    for white_char in '\t\r ':
        lines = [' '.join(wd for wd in line.split(white_char) if len(wd))
                 for line in lines]

    # Remove blank lines
    lines = [line for line in lines if len(line)]

    return '\n'.join(lines)


_DTYPES_TYPE_NAMES = {
    np.dtype('S1'): 'char',
    np.dtype('<U1'): 'char',
    np.dtype('int8'): 'byte',
    np.dtype('int16'): 'short',
    np.dtype('int32'): 'int',
    np.dtype('int64'): 'int64',
    np.dtype('float32'): 'float',
    np.dtype('float64'): 'double',
    np.dtype('uint8'): 'ubyte',
    np.dtype('uint16'): 'ushort',
    np.dtype('uint32'): 'uint',
    np.dtype('uint64'): 'uint64'
}

_DTYPES_ATTR_SUFFICES = {
    # Don't bother with chars/strings, we'll handle those specially
    np.dtype('int8'): 'b',
    np.dtype('int16'): 's',
    np.dtype('int32'): '',
    np.dtype('int64'): 'L',
    np.dtype('float32'): 'f',
    np.dtype('float64'): '',
    np.dtype('uint8'): 'UB',
    np.dtype('uint16'): 'US',
    np.dtype('uint32'): 'U',
    np.dtype('uint64'): 'UL'
}


def _bare_attr_cdl_string(attr):
    # Return a CDL string representing an attribute and its value.
    val = attr.value
    if isinstance(val, str):
        contents_str = '"{}"'.format(val)
        type_str = ''
    else:
        vals = np.array(val).flat[:]
        val_basetype = vals[0].dtype
        type_str = _DTYPES_ATTR_SUFFICES[val_basetype]
        val_strs = [repr(val) for val in vals]
        # Make a crude attempt to display arrays as numpy does ?
        # We currently don't do arrays of strings (??)
        # So strip '0's from after the dp
        val_strs_2 = []
        for val_str in val_strs:
            if '.' in val_str:
                before, after = val_str.split('.')
                while after.endswith('0'):
                    after = after[:-1]
                val_str = '{}.{}'.format(before, after)
            val_strs_2.append(val_str)
        contents_str = ', '.join(val_str + type_str for val_str in val_strs_2)
    return '{} = {}'.format(attr.name, contents_str)


def _attr_cdl_string(attr):
    # Return a full attribute CDL string, including the prefix and suffix.
    return ':{} ;'.format(_bare_attr_cdl_string(attr))


def _attr_cdl_lines(*args, **kwargs):
    # Return a list of CDL lines for an attribute.
    return [_attr_cdl_string(*args, **kwargs)]


def _dim_cdl_lines(dim):
    # Return a list of CDL lines for a dimension.
    len_str = 'UNLIMITED' if dim.unlimited else str(dim.length)
    dim_line = '{} = {} ;'.format(dim.name, len_str)
    return [dim_line]


#: The default indent spacing.
_N_INDENT_DEFAULT = 4


def _indent_lines(lines, n_indent=_N_INDENT_DEFAULT):
    # Prepend each of the lines with an indent string (spaces).
    indent = ' ' * n_indent
    return [indent + line for line in lines]


def _elements_lines(elements, cdl_lines_call, indent=_N_INDENT_DEFAULT):
    # Call a CDL-lines function for all of a container's contents, and return
    # the concatenation of all the result lines.
    el_lines = []
    for el_name in sorted(elements.names()):
        el_lines.extend(cdl_lines_call(elements[el_name]))
    return _indent_lines(el_lines, n_indent=indent)


def _var_cdl_lines(var):
    # Return a list of CDL lines for a variable.
    if var.dimensions:
        dims_str = '({})'.format(
            ', '.join(dim.name for dim in var.dimensions))
    else:
        dims_str = ''
    type_name = _DTYPES_TYPE_NAMES[var.data.dtype]
    result = '{} {}{} ;'.format(type_name, var.name, dims_str)
    result = [result]
    if var.attributes:
        def var_attr_cdl_lines(attr):
            return [var.name + _attr_cdl_string(attr)]
        result.extend(_elements_lines(var.attributes, var_attr_cdl_lines))
    return result


def _group_cdl_lines(group, at_root=True, indent=0,
                     plus_indent=_N_INDENT_DEFAULT):
    # Return a list of CDL lines for a group.
    next_indent = indent + plus_indent
    ind_str = ' ' * indent
    space_id = 'netcdf' if at_root else 'group:'
    result = '{} {} '.format(space_id, group.name) + '{'
    result = [result]
    if group.dimensions:
        result.extend(['', ind_str + 'dimensions:'])
        result.extend(_elements_lines(group.dimensions, _dim_cdl_lines,
                                      next_indent))
    if group.variables:
        result.extend(['', ind_str + 'variables:'])
        result.extend(_elements_lines(group.variables, _var_cdl_lines,
                                      next_indent))
    if group.attributes:
        class_name = 'global' if at_root else 'group'
        base_comment = '// {} attributes:'.format(class_name)
        result.extend(['', base_comment])
        result.extend(_elements_lines(group.attributes,
                                      _attr_cdl_lines,
                                      next_indent))
    if group.groups:
        group_indent = indent if at_root else next_indent

        def _spaced_grp_cdl_lines(g):
            return [''] + _group_cdl_lines(g, at_root=False,
                                           plus_indent=plus_indent)
        inner_groups_lines = _elements_lines(group.groups,
                                             _spaced_grp_cdl_lines,
                                             indent=group_indent)
        result.extend(inner_groups_lines)

    end_line = '}'
    if not at_root:
        end_line += ' // group {}'.format(group.name)
    result.append(end_line)

    return result


def cdl(element, indent=0, plus_indent=_N_INDENT_DEFAULT):
    """
    Make a CDL output string for an Ncobj element (aka NetCDF 'component').

    This attempts not just to produce valid CDL, but to replicate ncdump
    output.  However, it will still differ in indenting, output order, and
    possibly the comments.

    If all is well, the output of this, processed via
    :meth:`comparable_cdl`, should match 'ncdump' output, similarly
    processed.  However, there is a big caveat : this routine outputs all
    elements in alphabetical order, whereas 'ncdump' uses creation order
    (?apparently?).  NetCDF4 abstracts away file- or handle- order (as does
    ncobj).  You can get around this by re-saving the data, resulting in a file
    _written_ in the alphabetical ordering.

    Args:

    * element (:class:`ncobj.NcObj`):
        item to generate a representation of.

    * indent (int):
        a number of spaces to prefix all output lines.

    * plus_indent (int):
        indent interval to apply to inner parts.

    Returns:
        A single string with embedded newlines.

    .. note::

        Groups must be "complete" in the sense of
        :meth:`ncobj.grouping.complete`, or various errors can occur.

    """
    if isinstance(element, nco.Group):
        lines = _group_cdl_lines(element, indent=indent,
                                 plus_indent=plus_indent)
    elif isinstance(element, nco.Variable):
        lines = _var_cdl_lines(element)
    elif isinstance(element, nco.Attribute):
        lines = [_bare_attr_cdl_string(element)]
    elif isinstance(element, nco.Dimension):
        lines = _dim_cdl_lines(element)
    else:
        raise ValueError('{} is not a recognised NcObj element.'.format(
            element))

    return '\n'.join(lines)
