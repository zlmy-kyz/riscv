import sys
sys.path.insert(0, r'D:\riscv\RISCV\sim\write_buffer_two_entry')
import glob
from check_wb2 import parse

run = glob.glob(r'D:\riscv\RISCV\sim\write_buffer_two_entry\xs_probe_x16_20261018_d')[0]
edges, marks, summary, dump, init_mem, unknown, nd, pd = parse(run + r'\wb2.edges.log')
print('marks', marks, 'summary', summary)
for x in edges:
    print(x['cyc'], 'rst', x['rstn'], 'init', x['init'],
          '| dv', x['dv'], 'dr', x['dr'], 'dw', x['dw'], 'da', hex(x['da']), 'wd', hex(x['wd']),
          'ws', x['ws'], '| dsv', x['dsv'], 'dd', hex(x['ddata']),
          '| av', x['av'], 'ardy', x['ardy'], 'aa', hex(x['aa']),
          '| wrdy', x['wrdy'], 'wstrb', hex(x['wstrb']), 'wdata', hex(x['wdata'] & 0xffffffff),
          '| arv', x['arv'], 'ardy2', x['ardy2'], 'ara', hex(x['ara']),
          'rv', x['rv'], 'rid', x['rid'], 'busy', x['busy'])
