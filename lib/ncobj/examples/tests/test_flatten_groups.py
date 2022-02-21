"""
Examples demonstrating how to 'flatten' datasets with sub-groups :
Copy all input variables to top level, and rename to avoid any conflicts.

"""
import unittest as tests

from ncobj.shorts import og, od, ov, oa

from ncobj.examples.eg_flatten_groups import (
    flat_prefix_all, flat_prefix_whereneeded
)


class TestFlatten(tests.TestCase):
    def setUp(self):
        dx, dy, dz = od('x', 2), od('y', 3), od('z', 5)
        v1 = ov('v1', dd=[dx, dy])
        v2 = ov('v2', dd=[dx])
        v3 = ov('v3', dd=[dz])
        test_grp = og(
            'root',
            # NOTE: the extra dimension here is omitted from the output.
            dd = [dx, dy, od('dim_unused', 1)],
            vv = [v1, v2],
            gg = [
                og('inner',
                    dd=[dz],
                    vv=[v1, v3]
               ),
            ],
            # NOTE: attributes are discarded
            aa = [oa('attr_unused', 'this')]
        )
        self.dx = dx
        self.dy = dy
        self.dz = dz
        self.v1 = v1
        self.v2 = v2
        self.v3 = v3
        self.test_group = test_grp

    def test_flatten_allrenames(self):
        result = flat_prefix_all(self.test_group)
        dx, dy, dz = self.dx, self.dy, self.dz
        v1 = self.v1.detached_copy()
        v1.rename('root/v1')
        v2 = self.v2.detached_copy()
        v2.rename('root/v2')
        v1x = self.v1.detached_copy()
        v1x.rename('root/inner/v1')
        v3x = self.v3.detached_copy()
        v3x.rename('root/inner/v3')
        expect = og(
            '',
            dd=[dx, dy, dz],
            vv=[v1, v2, v1x, v3x]
        )
        self.assertEqual(expect, result)

    def test_flatten_onlyneededrenames(self):
        self.test_group.rename('root')
        result = flat_prefix_whereneeded(self.test_group)
        dx, dy, dz = self.dx, self.dy, self.dz
        v1 = self.v1.detached_copy()
        v1.rename('root/v1')
        v2 = self.v2
        v1x = self.v1.detached_copy()
        v1x.rename('root/inner/v1')
        v3x = self.v3
        expect = og(
            '',
            dd=[dx, dy, dz],
            # NOTE: variables re-ordered, having been collated by name
            vv=[v1, v1x, v2, v3x]
        )
        self.assertEqual(expect, result)


if __name__ == '__main__':
    tests.main()
