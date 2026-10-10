"""Maximum formal LOAD window; data only, never executed."""
import run
from cases import Builder

def selected(suite):
    b=Builder();b.ping('window_reset',new_epoch=True)
    raw=bytes((i*37+11)&255 for i in range(61440))
    b.image(raw,'max_61440');b.ping('max_complete_no_RUN');b.check_crc(raw)
    return b.cases

run.cases=selected
if __name__=='__main__':run.main()
