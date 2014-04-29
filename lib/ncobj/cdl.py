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


_DEBUG_COMPARABLE = False
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


def _var_attr_cdl(var, attr):
    if _DEBUG_CDL:
        print 'CDL_VAR_ATTR var({})', ncg.group_path(var)
    return var.name + _attr_cdl(attr)


def _attr_cdl(attr):
    val = attr.value
    if _DEBUG_CDL:
        print 'CDL_ATTR ({}) : type={}, val={!r}'.format(
            ncg.group_path(attr), type(val), val)
    type_str = 'L' if isinstance(val, int) else ''
    if isinstance(val, basestring):
        val_str = '"{}"'.format(val)
    else:
        if not hasattr(val, '__len__') or len(val) < 2:
            val_strs = [repr(val)]
        else:
            val_strs = [repr(oneval) for oneval in val]
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
        val_str = ', '.join(val_strs_2)
    return ':{} = {}{} ;'.format(attr.name, val_str, type_str)


def _dim_cdl(dim):
    if _DEBUG_CDL:
        print 'CDL_DIM ({}) : length={}, unlimited={}'.format(
            ncg.group_path(dim), dim.length, dim.unlimited)
    len_str = 'UNLIMITED' if dim.unlimited else str(dim.length)
    return '{} = {} ;'.format(dim.name, len_str)


_VAR_TYPE_NAMES = {
    np.dtype('float32'): 'float',
    np.dtype('float64'): 'double',
    np.dtype('int32'): 'int',
    np.dtype('int64'): 'long'}

_N_INDENT_DEFAULT = 4


def _indent_lines(lines, n_indent=None):
    if n_indent is None:
        n_indent = _N_INDENT_DEFAULT
    indent = ' ' * n_indent
    return '\n'.join(indent + line for line in lines.split('\n'))


def _elements_string(elements, cdl_call, indent=_N_INDENT_DEFAULT):
    el_lines = [cdl_call(elements[el_name])
                for el_name in sorted(elements.names())]
    els_str = ''.join('\n' + line for line in el_lines if line and len(line))
    return _indent_lines(els_str, indent)


def _var_cdl(var):
    if var.dimensions:
        dims_str = '({})'.format(
            ', '.join(dim.name for dim in var.dimensions))
    else:
        dims_str = ''
    if _DEBUG_CDL:
        print 'CDL_VAR ({}): type={}, dims=({})'.format(
            ncg.group_path(var), var.data.dtype, dims_str)
    type_name = _VAR_TYPE_NAMES[var.data.dtype]
    result = '{} {}{} ;'.format(type_name, var.name, dims_str)
    if var.attributes:
        att_strs = [var.name + _attr_cdl(var.attributes[attr_name])
                    for attr_name in sorted(var.attributes.names())]
        att_lines = ''.join('\n' + line for line in (att_strs))
        result += _indent_lines(att_lines, 8)
    return result


def _group_cdl(group, at_root=True, indent=0, plus_indent=4):
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
        result += _elements_string(group.attributes, _attr_cdl, next_indent)
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


def group_cdl(group, indent=0, plus_indent=4):
    """
    Create a CDL output string representing a :class:`ncobj.Group`.

    This attempts not just to produce valid CDL, but to replicate ncdump
    output.  It will still differ in indenting, etc.

    If all is well, the output of this, processed via
    :meth:`comparable_cdl`, should match 'ncdump' output, similarly
    processed.

    Args:

    * group (:class:`ncobj.Group`):
        group to generate representation of.

    * indent (int):
        a number of spaces to prefix all output lines.

    * plus_indent (int):
        indent interval to apply to inner parts.

    Returns:
        A single string with embedded newlines.

    .. note::

        'group' must be "complete" in the sense of
        :meth:`ncobj.grouping.complete`, or various errors can occur.

    """
    return _group_cdl(group, indent=indent, plus_indent=plus_indent,
                      at_root=True)
