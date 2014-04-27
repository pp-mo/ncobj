"""
Example code demonstrating simple semantic containers 'flatten' operation.

"""
import mock
import numpy as np

import ncobj as nco
import ncobj.grouping as ncg
import ncobj.cdl as ncdl

import ncobj.examples.simple_semantic_containers as egs


g = egs.eg_simple_grouped()
g_cdl = ncdl.group_cdl(g)

print
print '----------------'
print 'Original grouped version:'
print '----------------'
print g_cdl
print '----------------'

g_flattened = egs.flatten_grouped_containers(g)
g_flattened_cdl = ncdl.group_cdl(g_flattened)
print
print '----------------'
print 'Result, flattened from grouped form:'
print '----------------'
print g_flattened_cdl
print '----------------'

g_flat_eg = egs.eg_simple_flat()
#g_flat_eg_cdl = ncdl.group_cdl(g_flat_eg)
print
print 'Result matches flat-form reference : ', g_flattened == g_flat_eg