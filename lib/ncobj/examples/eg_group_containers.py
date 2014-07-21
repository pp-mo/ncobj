"""
Example code demonstrating simple semantic containers 'grouping' operation.

"""
import ncobj.cdl as ncdl

import ncobj.examples.simple_semantic_containers as egs


g = egs.eg_simple_flat()
g_cdl = ncdl.cdl(g)

print
print '----------------'
print 'Original flat version:'
print '----------------'
print g_cdl
print '----------------'

g_grouped = egs.group_flat_containers(g)
g_grouped_cdl = ncdl.cdl(g_grouped)
print
print '----------------'
print 'Result, grouped from flat form:'
print '----------------'
print g_grouped_cdl
print '----------------'

g_grouped_eg = egs.eg_simple_grouped()
print
print 'Result matches grouped-form reference : ', g_grouped == g_grouped_eg
