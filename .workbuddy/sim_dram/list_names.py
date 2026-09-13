import io, re
s = io.open('dram.vcd', encoding='utf-8', errors='replace').read()
i = s.index('$enddefinitions')
hdr = s[:i]
stack = []
for line in hdr.splitlines():
    line = line.strip()
    m = re.match(r'\$scope\s+(\S+)\s+(\S+)\s*\$end', line)
    if m:
        stack.append(m.group(2)); continue
    if line.startswith('$upscope'):
        if stack: stack.pop()
        continue
    m = re.match(r'\$var\s+(\S+)\s+(\d+)\s+(\S+)\s+([^\s]+)\s*\$end', line)
    if m:
        print('.'.join(stack + [m.group(4)]))
