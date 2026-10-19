import socket, errno
# connect to ::1 with nobody listening -> expect ECONNREFUSED (111/10061) if policy allows the connect
for i in range(3):
    s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    s.settimeout(1.0)
    try:
        s.connect(("::1", 59999))
        print("connect ::1:59999 UNEXPECTED OK")
    except OSError as e:
        print("connect ::1:59999 ->", e.errno, e.strerror)
    finally:
        s.close()
# same probe on IPv4 for calibration
for i in range(2):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    try:
        s.connect(("127.0.0.1", 59999))
        print("connect 127.0.0.1:59999 UNEXPECTED OK")
    except OSError as e:
        print("connect 127.0.0.1:59999 ->", e.errno, e.strerror)
    finally:
        s.close()
