"""Task030 same frozen P300/V300 board evidence review; no serial/PDS/RTL."""
import inspect,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'sim/mini_board_migration'))
import review_write_buffer_board as prior
import run_branch_isa_port_measurement as measurement
def main():
    source=inspect.getsource(prior.main)
    replacements=[
        ("folder=ROOT/'sim/mini_board_migration/board/coremark_i64_d64_zmmul_wbuf_300_01'",
         "folder=ROOT/'sim/cpu_branch_turnover/board/coremark_i64_d64_zmmul_bturn_300_01'"),
        ("prior=ROOT/'sim/mini_board_migration/board/coremark_i64_d64_zmmul_turnover_300_01'",
         "prior=ROOT/'sim/mini_board_migration/board/coremark_i64_d64_zmmul_sfwd_300_01'"),
        ("out=folder/'codex_review_20261013'","out=folder/'codex_review_20261014'"),
        ('WRITE_BUFFER_ACTUAL_DDR_P_V_RAW_EVIDENCE_AND_SAME_BIN_PERFORMANCE_REVIEW_PASS',
         'BRANCH_TURNOVER_ACTUAL_DDR_P_V_RAW_EVIDENCE_AND_SAME_BIN_PERFORMANCE_REVIEW_PASS')]
    for old,new in replacements:
        assert source.count(old)==1;source=source.replace(old,new,1)
    namespace=dict(prior.__dict__,tool=type('ReadOnlyVerifier',(),{'transport':measurement}))
    exec(compile(source,'<Task030_same_BIN_actual_UART_audit>','exec'),namespace);namespace['main']()
if __name__=='__main__':main()
