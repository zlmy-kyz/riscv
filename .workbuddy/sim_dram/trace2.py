import io, re

s = io.open('dram.vcd', encoding='utf-8', errors='replace').read()
i = s.index('$enddefinitions')
hdr, body = s[:i], s[i:]

stack = []
ID2NAME = {}
for line in hdr.splitlines():
    line = line.strip()
    m = re.match(r'\$scope\s+(\S+)\s+(\S+)\s*\$end', line)
    if m:
        stack.append(m.group(2)); continue
    if line.startswith('$upscope'):
        if stack: stack.pop()
        continue
    m = re.match(r'\$var\s+(\S+)\s+(\d+)\s+(\S+)\s+(.+?)\s*\$end', line)
    if m:
        ID2NAME[m.group(3)] = '.'.join(stack + [m.group(4).strip().split()[0]])

PRE = 'tb_dram.u_data_ram.U_ipml_spram_data_ram.ADDR_LOOP[0].DATA_LOOP[0].U_GTP_DRM36K_E1.'
WRAP = 'tb_dram.u_data_ram.'
TOP = 'tb_dram.'

WANT = [
    (TOP + 'resetn',                   'clk/rstn'),
    (WRAP + 'rst',                     'wrap.rst'),
    (WRAP + 'wr_en',                   'wrap.wr_en'),
    (WRAP + 'addr',                    'wrap.addr'),
    (PRE + 'RSTA',                     'RSTA'),
    (PRE + 'rsta_int',                 'rsta_int'),
    (PRE + 'CEA',                      'CEA'),
    (PRE + 'CSA',                      'CSA'),
    (PRE + 'WEA',                      'WEA'),
    (PRE + 'ADDRA',                    'ADDRA'),
    (PRE + 'DIA',                      'DIA'),
    (PRE + 'csa_reg',                  'csa_reg'),
    (PRE + 'wea_reg',                  'wea_reg'),
    (PRE + 'ada_reg',                  'ada_reg'),
    (PRE + 'cas_inta',                 'cas_inta'),
    (PRE + 'cas_sela',                 'cas_sela'),
    (PRE + 'write_en_a',               'write_en_a'),
    (PRE + 'read_en_a',                'read_en_a'),
    (PRE + 'a_out',                    'a_out'),
    (WRAP + 'rd_data',                 'wrap.rd_data'),
]

name2id = {v: k for k, v in ID2NAME.items()}
pairs = [(lbl, name2id[nm]) for nm, lbl in WANT if nm in name2id]
print('missing:', [nm for nm, lbl in WANT if nm not in name2id])
print('t(ns) | ' + ' | '.join(l for l, _ in pairs))
print('-' * 190)

state = {vid: 'x' for _, vid in pairs}
rows = []
pending = {}
for line in body.splitlines():
    line = line.strip()
    if not line or line.startswith('$'):
        continue
    if line.startswith('#'):
        for k, v in pending.items():
            state[k] = v
        pending = {}
        t = int(line[1:]) / 100.0          # VCD timescale here = 10ps -> ns
        rows.append((t, [state[v] for _, v in pairs]))
        continue
    c = line[0]
    if c in '01xz':
        vid = line[1:]
        if vid in state:
            pending[vid] = c
    elif c in 'bB':
        p = line.split()
        if len(p) == 2 and p[1] in state:
            pending[p[1]] = p[0][1:]

for tt, row in rows:
    if 90 <= tt <= 140:
        print('%6.1f | ' % tt + ' | '.join(row))
