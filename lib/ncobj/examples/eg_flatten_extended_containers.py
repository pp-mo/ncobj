"""
Example code demonstrating 'flatten' operation for enhanced semantic containers
definition.

"""
from ncobj.cdl import cdl

import ncobj.examples.semantic_containers as egs
#from ncobj.tests.cdl.test_cdl import print_linewise_diffs


g = egs.eg_simple_grouped()
g_cdl = cdl(g)

print
print '----------------'
print 'Original grouped version:'
print '----------------'
print g_cdl
print '----------------'

g_flattened = egs.flatten_grouped_containers(g)
g_flattened_cdl = cdl(g_flattened)
print
print '----------------'
print 'Result, flattened from grouped form:'
print '----------------'
print g_flattened_cdl
print '----------------'

g_flat_eg = egs.eg_simple_flat()
#g_flat_eg_cdl = cdl(g_flat_eg)
#print
#print '----------------'
#print 'ORIGINAL flat form:'
#print '----------------'
#print g_flat_eg_cdl
#print '----------------'

print
print 'Result matches flat-form reference : ', g_flattened == g_flat_eg

#print_linewise_diffs('original-flat', 'groups,flattened',
#                     g_flat_eg_cdl, g_flattened_cdl)
