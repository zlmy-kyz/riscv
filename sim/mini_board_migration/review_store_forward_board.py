"""Task029 actual UART and same frozen BIN comparison; no serial/PDS."""
import inspect
import review_write_buffer_board as prior
import run_store_forward_measurement as measurement

def main():
    source=inspect.getsource(prior.main)
    replacements=[
        ("folder=ROOT/'sim/mini_board_migration/board/coremark_i64_d64_zmmul_wbuf_300_01'",
         "folder=ROOT/'sim/mini_board_migration/board/coremark_i64_d64_zmmul_sfwd_300_01'"),
        ("prior=ROOT/'sim/mini_board_migration/board/coremark_i64_d64_zmmul_turnover_300_01'",
         "prior=ROOT/'sim/mini_board_migration/board/coremark_i64_d64_zmmul_dread_300_01'"),
        ("out=folder/'codex_review_20261013'","out=folder/'codex_review_20261014'"),
        ('WRITE_BUFFER_ACTUAL_DDR_P_V_RAW_EVIDENCE_AND_SAME_BIN_PERFORMANCE_REVIEW_PASS',
         'STORE_FORWARD_ACTUAL_DDR_P_V_RAW_EVIDENCE_AND_SAME_BIN_PERFORMANCE_REVIEW_PASS')]
    for old,new in replacements:
        assert source.count(old)==1
        source=source.replace(old,new,1)
    namespace=dict(prior.__dict__,tool=type('ReadOnlyVerifier',(),{'transport':measurement}))
    exec(compile(source,'<Task029_same_BIN_actual_UART_audit>','exec'),namespace)
    namespace['main']()
if __name__=='__main__':main()
