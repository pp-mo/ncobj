"""
Example code demonstrating 'flatten' operation for enhanced semantic containers
definition.

"""
from ncobj.cdl import cdl

import ncobj.examples.semantic_containers as egs


g = egs.eg_simple_flat()
g_cdl = cdl(g)

print
print '----------------'
print 'Original flat version:'
print '----------------'
print g_cdl
print '----------------'

g_grouped = egs.group_flat_containers(g)
g_grouped_cdl = cdl(g_grouped)
print
print '----------------'
print 'Result, grouped from flat form:'
print '----------------'
print g_grouped_cdl
print '----------------'

g_grp_eg = egs.eg_simple_grouped()

print
print 'Result matches groups-form reference : ', g_grouped == g_grp_eg
