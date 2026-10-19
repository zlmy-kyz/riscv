import socket
ok = fail = 0
ports = []
for i in range(20):
    s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    try:
        s.bind(("::1", 0)); s.listen(1)
        p = s.getsockname()[1]
        c = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        try:
            c.connect(("::1", p)); ok += 1; ports.append(("OK", p))
        finally:
            c.close()
    except OSError as e:
        fail += 1; ports.append(("FAIL%d" % e.errno, p if 'p' in dir() else -1))
    finally:
        s.close()
print("ok=%d fail=%d" % (ok, fail))
print(ports[:8])
