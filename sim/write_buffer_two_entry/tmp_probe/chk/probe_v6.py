import socket
def t(label, fam, addr):
    s = socket.socket(fam, socket.SOCK_STREAM)
    try:
        s.bind((addr, 0)); s.listen(1)
        port = s.getsockname()[1]
        c = socket.socket(fam, socket.SOCK_STREAM)
        try:
            c.connect((addr, port)); print(label, "CONNECT OK", port)
        finally:
            c.close()
    except OSError as e:
        print(label, "FAIL", e.errno, e.strerror)
    finally:
        s.close()
t("v6", socket.AF_INET6, "::1")
t("v4", socket.AF_INET, "127.0.0.1")
