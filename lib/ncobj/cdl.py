"""
Utility to produce a CDL-style readable output summary for an
:class:`ncobj.Group`.

Output is designed to be similar to "ncdump -h".  Variables data is completely
omitted.

Also includes a function to 'canonicalise' results for comparison with actual
ncdump output.

Extra notes:

 * The rendering of attribute values is still very primitive, and may not
    always work properly.

 * Only ncobj supported features are managed (so no user-types at all).

 * Attributes containing vectors of strings are not handled, but at present
    netCDF4-python can not manage these anyway.

"""
import numpy as np


import ncobj as nco


_DEBUG_CDL = False

if _DEBUG_CDL:
    import ncobj.grouping as ncg

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


def _attr_cdl(attr):
    val = attr.value
    if _DEBUG_CDL:
        print 'CDL_ATTR ({}) : type={}, val={!r}'.format(
            ncg.group_path(attr), type(val), val)
    if isinstance(val, basestring):
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


def _wrapped_attr_cdl(attr):
    return ':{} ;'.format(_attr_cdl(attr))


def _dim_cdl(dim):
    if _DEBUG_CDL:
        print 'CDL_DIM ({}) : length={}, unlimited={}'.format(
            ncg.group_path(dim), dim.length, dim.unlimited)
    len_str = 'UNLIMITED' if dim.unlimited else str(dim.length)
    return '{} = {} ;'.format(dim.name, len_str)


_N_INDENT_DEFAULT = 4


def _indent_lines(lines, n_indent=None):
    if n_indent is None:
        n_indent = _N_INDENT_DEFAULT
    indent = ' ' * n_indent
    return '\n'.join(indent + line for line in lines.split('\n'))


def _elements_string(elements, cdl_call, indent=_N_INDENT_DEFAULT):
    el_lines = [cdl_call(elements[el_name])
                for el_name in sorted(elements.names())]
    els_str = '\n'.join(line for line in el_lines if line and len(line))
    els_str = _indent_lines(els_str, indent)
    if len(els_str) != 0:
        els_str = '\n' + els_str
    return els_str


def _var_cdl(var):
    if var.dimensions:
        dims_str = '({})'.format(
            ', '.join(dim.name for dim in var.dimensions))
    else:
        dims_str = ''
    if _DEBUG_CDL:
        print 'CDL_VAR ({}): type={}, dims=({})'.format(
            ncg.group_path(var), var.data.dtype, dims_str)
    type_name = _DTYPES_TYPE_NAMES[var.data.dtype]
    result = '{} {}{} ;'.format(type_name, var.name, dims_str)
    if var.attributes:
        def var_attr_cdl(attr):
            return var.name + _wrapped_attr_cdl(attr)
        result += _elements_string(var.attributes, var_attr_cdl)
    return result


def _group_cdl(group, at_root=True, indent=0, plus_indent=_N_INDENT_DEFAULT):
    if _DEBUG_CDL:
        print 'CDL_GROUP ({})'.format(ncg.group_path(group))
    next_indent = indent + plus_indent
    ind_str = '\n' + ' ' * indent
    space_id = 'netcdf' if at_root else 'group:'
    result = '{} {} '.format(space_id, group.name) + '{'
    if group.dimensions:
        result += '\n' + ind_str + 'dimensions:'
        result += _elements_string(group.dimensions, _dim_cdl, next_indent)
    if group.variables:
        result += '\n' + ind_str + 'variables:'
        result += _elements_string(group.variables, _var_cdl, next_indent)
    if group.attributes:
        result += '\n'
        class_name = 'global' if at_root else 'group'
        base_comment = '\n// {} attributes:'.format(class_name)
        result += base_comment
        result += _elements_string(group.attributes, _wrapped_attr_cdl,
                                   next_indent)
    if group.groups:
        result += '\n'
        group_indent = indent if at_root else next_indent
        _grp_cdl = lambda g: _group_cdl(g, at_root=False,
                                        plus_indent=plus_indent)
        result += _elements_string(group.groups, _grp_cdl, indent=group_indent)

    result += '\n}'
    if not at_root:
        result += ' // group {}'.format(group.name)
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
        result = _group_cdl(element, indent=indent, plus_indent=plus_indent,
                            at_root=True)
    elif isinstance(element, nco.Variable):
        result = _var_cdl(element)
    elif isinstance(element, nco.Attribute):
        result = _attr_cdl(element)
    elif isinstance(element, nco.Dimension):
        result = _dim_cdl(element)
    else:
        raise ValueError( '{} is not a recognised NcObj element.'.format(
            element))
    return result

