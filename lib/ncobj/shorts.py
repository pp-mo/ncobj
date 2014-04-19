"""Convenient shorthands for NcObj element constructors."""
import ncobj as nco


def og(name, aa=None, dd=None, vv=None, gg=None):
    return nco.Group(name,
                     dimensions=dd,
                     variables=vv,
                     attributes=aa,
                     sub_groups=gg)


def oa(name, v=None):
    return nco.Attribute(name, value=v)


def od(name, l=None, u=False):
    return nco.Dimension(name, length=l, unlimited=u)


def ov(name, dd=None, aa=None, data=None):
    return nco.Variable(name, dimensions=dd, attributes=aa,
                        dtype=None, data=data)
