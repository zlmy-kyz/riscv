import re
lines = [l.rstrip() for l in open('vsim_dbg.txt', errors='replace')]
dbg = [l for l in lines if 'DBG cyc=' in l]
print("total dbg", len(dbg))
for l in dbg[-24:]:
    print(l.strip())
print("=== marks ===")
for l in open('wb2.edges.log'):
    if l.startswith('M '):
        print(l.strip())
