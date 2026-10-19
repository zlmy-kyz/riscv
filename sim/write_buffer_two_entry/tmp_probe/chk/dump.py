import sys
COLS = "cyc resetn init iv ir isv ia idata dv dw ds dr da wd ws dsv ddata awvalid awready awaddr wdata wstrb wready arvalid arready araddr rvalid rid rlast rdata busy".split()
lines = [l.split() for l in open('wb2.edges.log') if l.startswith('E ')]
want = ('cyc','iv','ir','isv','idata','dv','dr','da','dsv','ddata','arvalid','arready','araddr','rvalid','rid','rdata','busy')
for w in lines:
    d = dict(zip(COLS, w[1:]))
    c = int(d['cyc'])
    if 55 <= c <= 78:
        print(' '.join('%s=%s' % (k, d[k]) for k in want))
