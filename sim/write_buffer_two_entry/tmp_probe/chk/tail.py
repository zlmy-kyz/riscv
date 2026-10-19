lines = open('wb2.edges.log').read().splitlines()
print("total", len(lines))
for l in lines[-3:]:
    print(repr(l[:160]))
