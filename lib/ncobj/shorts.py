"""Convenient shorthands for NcObj element constructors."""
import ncobj
import ncobj as nco


def og(name, aa=None, dd=None, vv=None, gg=None):
    """
    Shortform :class:`ncobj.Group` constructor.

    Args:

    * aa (iterable of :class:`ncobj.Attribute`):
        attributes
    * dd (iterable of :class:`ncobj.Dimension`):
        dimensions
    * vv (iterable of :class:`ncobj.Variable`):
        variables
    * gg (iterable of :class:`ncobj.Group`):
        (sub-)groups


    """
    return nco.Group(name,
                     dimensions=dd,
                     variables=vv,
                     attributes=aa,
                     sub_groups=gg)


def oa(name, v=None):
    """
    Shortform :class:`ncobj.Attribute` constructor.

    Args:

    * v (array-like scalar or vector):
        value

    """
    return nco.Attribute(name, value=v)


def od(name, l=None, u=False):
    """
    Shortform :class:`ncobj.Dimension` constructor.

    Args:

    * l (int):
        length
    * u (bool):
        unlimited

    """
    return nco.Dimension(name, length=l, unlimited=u)


def ov(name, dd=None, aa=None, data=None):
    """
    Shortform :class:`ncobj.Variable` constructor.

    Args:

    * dd (iterable of :class:`ncobj.Dimension`):
        dimensions
    * aa (iterable of :class:`ncobj.Attribute`):
        attributes
    * data (array-like):
        data

    """
    return nco.Variable(name, dimensions=dd, attributes=aa,
                        dtype=None, data=data)
