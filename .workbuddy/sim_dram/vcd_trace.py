import io, re

# --- parse VCD properly: $var <type> <width> <id> <name> $end ---
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
        var_id = m.group(3)          # <id>  -> the token used in the value section
        var_name = m.group(4).strip()
        ID2NAME[var_id] = '.'.join(stack + [var_name.split()[0]])

# signals we care about (by the tail of the hierarchical name)
WANT = {
    'addr': 'wrap.addr',
    'wr_en': 'wrap.wr_en',
    'wr_data': 'wrap.wr_data',
    'rd_data': 'wrap.rd_data',
    'rst': 'wrap.rst',
    'cs_bit0': 'ipm.cs_bit0',
    'cs_bit1_bus': 'ipm.cs_bit1',
    'cs_bit2_bus': 'ipm.cs_bit2',
    'csa_reg': 'drm.csa_reg',
    'wea_reg': 'drm.wea_reg',
    'bea_reg': 'drm.bea_reg',
    'CSA': 'drm.CSA',
    'WEA': 'drm.WEA',
    'CSB': 'drm.CSB',
    'da_reg': 'drm.da_reg',
    'DIA': 'drm.DIA',
    'cas_inta': 'drm.cas_inta',
    'cas_sela': 'drm.cas_sela',
    'write_en_a': 'drm.write_en_a',
    'read_en_a': 'drm.read_en_a',
    'ada_reg': 'drm.ada_reg',
    'rsta_int': 'drm.rsta_int',
    'rd_data_d': 'ipm.rd_data_d',
    'douta': 'drm.douta',
}

sel = {}   # label -> id
for vid, name in ID2NAME.items():
    tail = name.split('.')[-1]
    if tail not in WANT:
        continue
    label = WANT[tail]
    # only keep the DRM-instance copy for drm.* labels
    if label.startswith('drm.') and 'U_GTP_DRM36K_E1' not in name:
        continue
    if label.startswith('ipm.') and 'U_ipml_spram_data_ram' not in name:
        continue
    if label.startswith('wrap.') and name.count('.') != 2:
        continue
    sel.setdefault(label, vid)

order = ['wrap.addr', 'wrap.wr_en', 'wrap.wr_data', 'wrap.rst',
         'ipm.cs_bit0', 'ipm.cs_bit1', 'ipm.cs_bit2',
         'drm.csa_reg', 'drm.wea_reg', 'drm.bea_reg',
         'drm.cas_inta', 'drm.cas_sela', 'drm.write_en_a', 'drm.ada_reg',
         'drm.rsta_int', 'drm.CSA', 'drm.WEA', 'drm.CSB', 'drm.da_reg', 'drm.DIA']
pairs = [(l, sel[l]) for l in order if l in sel]
print('missing:', [l for l in order if l not in sel])
print('time | ' + ' | '.join(l for l, _ in pairs))
print('-' * 160)

state = {vid: 'x' for _, vid in pairs}
t = 0
rows = []

def commit_and_snap(new_t):
    rows.append((new_t, [state[vid] for _, vid in pairs]))

pending = {}
for line in body.splitlines():
    line = line.strip()
    if not line:
        continue
    if line.startswith('#'):
        for k, v in pending.items():
            state[k] = v
        pending = {}
        t = int(line[1:])
        commit_and_snap(t)
        continue
    if line.startswith('$'):
        continue
    c = line[0]
    if c in '01xz':
        vid = line[1:]
        if vid in state:
            pending[vid] = c
    elif c in 'bB':
        parts = line.split()
        if len(parts) == 2:
            vid = parts[1]
            if vid in state:
                pending[vid] = parts[0][1:]

for tt, row in rows:
    if 90000 <= tt <= 140000:   # VCD timescale = 10ps, so 1000 counts = 10ns
        print('%5d | ' % tt + ' | '.join(row))
