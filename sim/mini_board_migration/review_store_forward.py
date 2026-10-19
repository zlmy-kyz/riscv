"""Task029 independent raw review, reusing the verified audit contract without HDL."""
import inspect
import review_data_read_overlap as previous
import run_store_forward as stage
def main():
    source=inspect.getsource(previous.main)
    for old,new in [('DATA_READ_OVERLAP_KEY_PASS','STORE_FORWARD_KEY_PASS'),
        ('DATA_READ_OVERLAP_RAW_EVIDENCE_REVIEW_PASS','STORE_FORWARD_RAW_EVIDENCE_REVIEW_PASS'),
        ('tb_data_read_overlap_x32','tb_store_forward_x32')]:
        assert old in source;source=source.replace(old,new)
    namespace=dict(previous.__dict__)
    for n in ('ROOT','HERE','TAG','MANIFEST','MS','require_inputs','compile_argv','job_argv','check_job','sha','read','write'):
        namespace[n]=getattr(stage,n)
    exec(compile(source,'<Task029_raw_evidence_audit>','exec'),namespace);namespace['main']()
if __name__=='__main__':main()
