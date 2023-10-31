import unittest as tests


import ncobj as nco
import ncobj.grouping as ncg
from ncobj.shorts import og, od, ov, oa


from ncobj.examples.simple_semantic_containers import \
    flatten_grouped_containers, group_flat_containers, \
    eg_simple_flat, eg_simple_grouped


class Test_grouped_containers(tests.TestCase):
    def setUp(self):
        # make a really simple grouped structure
        self.g_simple_grouped_plain = \
            og('root', vv=[ov('global_var')],
               gg=[og('subgroup', vv=[ov('local_var')])])
        # make a separate grouped version with ':container_type=simple'
        self.g_simple_grouped_explicit = \
            og('root', vv=[ov('global_var')],
               gg=[og('subgroup', vv=[ov('local_var')],
                      aa=[oa('container_type', 'simple')])])
        # make an equivalent flat structure
        self.g_simple_flat = \
            og('root',
               vv=[ov('global_var'),
                   ov('subgroup___local_var'),
                   ov('subgroup', data=[0],
                      aa=[oa('container_type', 'simple'),
                          oa('members', 'subgroup___local_var')])])

    def test_simple_g2f(self):
        g = self.g_simple_grouped_plain
        g_flat = flatten_grouped_containers(g)
        self.assertEqual(g_flat, self.g_simple_flat)

    def test_simple_f2g(self):
        g = self.g_simple_flat
        g_grouped = group_flat_containers(g)
        self.assertEqual(g_grouped, self.g_simple_grouped_explicit)

    def test_roundtrip_g2f_f2g(self):
        g = self.g_simple_grouped_explicit
        g = group_flat_containers(flatten_grouped_containers(g))
        self.assertEqual(g, self.g_simple_grouped_explicit)

    def test_roundtrip_f2g_g2f(self):
        g = self.g_simple_flat
        g = flatten_grouped_containers(group_flat_containers(g))
        self.assertEqual(g, self.g_simple_flat)


class Test_eg_simple(tests.TestCase):
    def test_g2f(self):
        g_f = eg_simple_flat()
        g_g = eg_simple_grouped()
        g_g2f = flatten_grouped_containers(g_g)
        self.assertEqual(g_g2f, g_f)

    def test_f2g(self):
        g_f = eg_simple_flat()
        g_g = eg_simple_grouped()
        g_f2g = group_flat_containers(g_f)
        self.assertEqual(g_f2g, g_g)


if __name__ == '__main__':
    tests.main()
