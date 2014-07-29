"""
Example code demonstrating 'flatten' operation for enhanced semantic containers
definition.

"""
from ncobj.cdl import cdl

import ncobj.examples.semantic_containers as egs
#from ncobj.tests.cdl.test_cdl import print_linewise_diffs


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
#g_grp_eg_cdl = cdl(g_grp_eg)
#print
#print '----------------'
#print 'ORIGINAL grouped form:'
#print '----------------'
#print g_grp_eg_cdl
#print '----------------'

print
print 'Result matches groups-form reference : ', g_grouped == g_grp_eg

#print_linewise_diffs('original-grouped', 'flat,grouped',
#                     g_grp_eg_cdl, g_grouped_cdl)
