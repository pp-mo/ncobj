"""
Example code demonstrating simple semantic containers 'flatten' operation.

"""
from ncobj.cdl import cdl

import ncobj.examples.simple_semantic_containers as egs


g = egs.eg_simple_grouped()
g_cdl = cdl(g)

print()
print('----------------')
print('Original grouped version:')
print('----------------')
print(g_cdl)
print('----------------')

g_flattened = egs.flatten_grouped_containers(g)
g_flattened_cdl = cdl(g_flattened)
print()
print('----------------')
print('Result, flattened from grouped form:')
print('----------------')
print(g_flattened_cdl)
print('----------------')

g_flat_eg = egs.eg_simple_flat()
print()
print('Result matches flat-form reference : ', g_flattened == g_flat_eg)
