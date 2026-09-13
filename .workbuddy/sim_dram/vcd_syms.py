import io, re, sys

s = io.open('dram.vcd', encoding='utf-8', errors='replace').read()
i = s.index('$enddefinitions')
hdr, body = s[:i], s[i:]

# build full hierarchical name per symbol
stack = []
sym2name = {}
scope_pat = re.compile(r'\$scope\s+(\S+)\s+(\S+)\s*\$end')
var_pat = re.compile(r'\$var\s+(\S+)\s+(\d+)\s+(\S+)\s+([^\s]+)\s*\$end')
for line in hdr.splitlines():
    line = line.strip()
    m = scope_pat.match(line)
    if m:
        stack.append(m.group(2)); continue
    if line.startswith('$upscope'):
        if stack: stack.pop()
        continue
    m = var_pat.match(line)
    if m:
        sym2name[m.group(3)] = '.'.join(stack + [m.group(4)])

watch = ['csa_reg', 'ada_reg', 'wea_reg', 'bea_reg', 'cs_bit0', 'cas_inta',
         'addr_bus', 'wr_en', 'a_out', 'ba_out', 'csb_reg', 'web_reg', 'rd_data', 'rst']
sel = {k: v for k, v in sym2name.items()
       if any(k in w for w in watch)}
for k, v in sorted(sel.items(), key=lambda x: x[1]):
    print('%-4s %s' % (k, v))
