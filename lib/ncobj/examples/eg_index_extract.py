import numpy as np
from ncobj import Group, Variable, Dimension
from ncobj.shorts import og, ov, od
import ncobj.grouping as ncg
from collections import Iterable
from ncobj.cdl import cdl

class GroupExtractor(object):
    """
    An object which can index a `ncobj.Group` over dimensions.

    For example:
        selection = GroupExtractor(group, 'time', 'experiment')[:20, 3]

    """
    def __init__(self, group, *dims):
        """
        Create an extractor over specified dimensions of a group.

        Args:

        * group (`ncobj.Group`):
            the source group to extract from.
        * dims (iterable of `ncobj.Dimension` or string):
            dimensions to index over.

        """
        self._group = group.detached_copy()

        def _getdim(dim):
            # Parse and check dimension inputs.
            dim_name = dim.name if isinstance(dim, Dimension) else dim
            dim = group.dimensions.get(dim_name)
            if dim is None:
                raise ValueError('specified group has no dimension '
                                 'named "{}".'.format(dim_name))
            return dim

        self._dims = [_getdim(dim) for dim in dims]

    def __getitem__(self, keys):
        """
        Return an extracted sub-section of the contained group.

        The specified extractor dimensions are indexed as required.
        The result is a completed group based on the original.

        """
        if not isinstance(keys, Iterable):
            keys = [keys]
        #print 'index by:', keys
        group = self._group.detached_copy()
        for index, dim in zip(keys, self._dims):
            #print 'slice {} by {}'.format(dim, index)
            dim_name = dim.name
            dim_reduces = not isinstance(index, slice)
            # Slice all variables that map this dimension
            for var in ncg.all_variables(group):
                #print 'var before:', var
                var_inds = [index if this_dim.name == dim_name else slice(None)
                            for this_dim in var.dimensions]
                #print 'var_inds = ', var_inds
                var.data = var.data[tuple(var_inds)]
                if dim_reduces:
                    var_dims = [this_dim for this_dim in var.dimensions
                                if this_dim.name != dim_name]
                    var.dimensions = var_dims
                    #print 'var_dims = ', var_dims
                #print 'var after:', var, 'shape = ', var.data.shape

            # Remove the dimension if we indexed it away.
            if dim_reduces:
                #print 'removed ', dim
                group.dimensions.remove(dim)
        ncg.complete(group)
        return group

test_group = og(
    'test',
    dd=[od('y', 3), od('x', 4)],
    vv=[ov('a_x', dd=[od('x')], data=np.array([1, 2, 3, 4])),
        ov('a_y', dd=[od('y')], data=np.array([11, 12, 13])),
        ov('a_yx', dd=[od('y'), od('x')], data=np.arange(12).reshape((3, 4))),
        ov('a_xy', dd=[od('x'), od('y')], data=np.arange(12).reshape((4, 3)))]
)


def show_results(extracted):
    #print extracted
    print cdl(extracted)
    print 'vars data: \n' + '\n'.join("{}:{}".format(var.name, var.data)
                                      for var in ncg.all_variables(extracted))

print 'original'
show_results(test_group)

extract = GroupExtractor(test_group, 'x', 'y')

print
print '-------------'
print 'x,y[1,2]'
show_results(extract[1, 2])

print
print '-------------'
print 'x,y[2]'
show_results(extract[2])

print
print '-------------'
print 'x,y[:, 2]'
show_results(extract[:, 2])

print
print '-------------'
print 'x,y[:2]'
show_results(extract[:2])

print
print '-------------'
print 'x,y[:, 2:]'
show_results(extract[:, 2:])
