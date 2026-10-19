import socket
for fam, addr in ((socket.AF_INET6, "::1"), (socket.AF_INET, "127.0.0.1")):
    s = socket.socket(fam, socket.SOCK_STREAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((addr, 0))
        s.listen(1)
        port = s.getsockname()[1]
        c = socket.socket(fam, socket.SOCK_STREAM)
        c.connect((addr, port))
        print(fam, addr, "listen+connect OK port", port)
        c.close()
    except OSError as e:
        print(fam, addr, "FAIL", e)
    finally:
        s.close()
