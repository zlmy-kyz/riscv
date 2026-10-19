import socket
def t(label, fn):
    try:
        r = fn(); print(label, "OK", r)
    except OSError as e:
        print(label, "FAIL", e.errno, e.winerror if hasattr(e,'winerror') else '', e.strerror)

s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
t("v6 bind", lambda: s.bind(("::1", 0)))
port = s.getsockname()[1]
t("v6 listen", lambda: s.listen(1))
c = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
t("v6 connect", lambda: c.connect(("::1", port)))
c2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
t("v4connect-to-v6port", lambda: c2.connect(("127.0.0.1", port)))
