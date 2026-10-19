import sys
sys.path.insert(0, r'D:\riscv\RISCV\sim\write_buffer_two_entry')
from check_wb2 import parse

import glob
run = glob.glob(r'D:\riscv\RISCV\sim\write_buffer_two_entry\xs_probe_edge2_20261018_d')[0]
edges, marks, summary, dump, init_mem, unknown, nd, pd = parse(run + r'\wb2.edges.log')
print('marks', marks)
lo = max(0, len(edges) - 40)
for x in edges[lo:]:
    print(x['cyc'], 'rst', x['rstn'], 'init', x['init'],
          '| iv', x['iv'], 'ir', x['ir'], 'isv', x['isv'], 'ia', hex(x['ia']),
          'idata', hex(x['idata']),
          '| dv', x['dv'], 'dr', x['dr'], 'dw', x['dw'], 'da', hex(x['da']),
          '| av', x['av'], 'ardy', x['ardy'], 'aa', hex(x['aa']),
          '| wrdy', x['wrdy'], 'arv', x['arv'], 'ardy2', x['ardy2'],
          'ara', hex(x['ara']), 'rv', x['rv'], 'rid', x['rid'], 'busy', x['busy'])
