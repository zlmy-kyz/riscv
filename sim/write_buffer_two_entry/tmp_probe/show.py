import sys
p = sys.argv[1]
n = int(sys.argv[2]) if len(sys.argv) > 2 else 40
data = open(p, 'rb').read()
txt = data.decode('utf-8', 'replace')
lines = txt.replace('\r\n', '\n').replace('\r', '\n').split('\n')
shown = 0
for line in lines:
    line = ''.join(ch if (32 <= ord(ch) < 127 or ch in '\t') else '.' for ch in line)
    print(line)
    shown += 1
    if shown >= n:
        break
print('--- total lines:', len(lines), 'bytes:', len(data))
