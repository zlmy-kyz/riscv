import sys
sys.path.insert(0, r'D:\riscv\RISCV\sim\write_buffer_two_entry')
from compare_fair import load

for d in (r'xs_probe_20261018_d', r'xs_probe_d2_20261018_d'):
    e, _, _ = load(d)
    seg = [x for x in e if 9 <= x['cyc'] <= 50]
    print(d)
    print('  dblock', [x['cyc'] for x in seg if x['dv'] and not x['dr']])
    print('  acc   ', [(x['cyc'], x['dw'], hex(x['da'])) for x in seg if x['dv'] and x['dr']])
    print('  aw    ', [(x['cyc'], hex(x['awaddr'])) for x in seg if x['awvalid'] and x['awready']])
    print('  w     ', [(x['cyc'], hex(x['awaddr'])) for x in seg
                       if x['wready'] and x['busy'] and x['wstrb']])
