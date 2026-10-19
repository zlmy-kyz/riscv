COLS = "cyc resetn init iv ir isv ia idata dv dw ds dr da wd ws dsv ddata awvalid awready awaddr wdata wstrb wready arvalid arready araddr rvalid rid rlast rdata busy".split()
for l in open('wb2.edges.log'):
    if not l.startswith('E '): continue
    w = l.split()
    d = dict(zip(COLS, w[1:]))
    c = int(d['cyc'])
    if 66 <= c <= 76:
        print('cyc=%s rst=%s init=%s iv=%s ir=%s isv=%s idata=%s dv=%s dw=%s dr=%s da=%s dsv=%s ddata=%s busy=%s' % (
            d['cyc'], d['resetn'], d['init'], d['iv'], d['ir'], d['isv'], d['idata'],
            d['dv'], d['dw'], d['dr'], d['da'], d['dsv'], d['ddata'], d['busy']))
