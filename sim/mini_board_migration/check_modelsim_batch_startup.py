"""One supported batch-mode startup preflight: no design, no run, no HDL/PDS/serial."""
import json
from resume_inst_drm64 import HERE, MS, command
from resume_inst_drm64_cli import require_inputs
from resume_inst_cache32 import pds_shell_count

require_inputs()
assert pds_shell_count()==0,'User PDS running; stop before tool startup'
out=HERE/'build/inst_drm64_preparation_20261013_a/batch_startup_preflight'
out.mkdir(exist_ok=False)
result=dict(status='RUNNING',scope='Tool startup only; no design top/library, run command or HDL time',
    HDL_run=False,host_settings_changed=False,PDS_started=False,serial_opened=False)
try:
    argv=[MS/'vsim.exe','-batch','-logfile',out/'transcript',
        '-do','puts {MODELSIM_BATCH_STARTUP_OK}; quit -f -code 0']
    log=command(argv,out,out/'startup',15)
    assert 'MODELSIM_BATCH_STARTUP_OK' in log and 'RPC_Init:' not in log
    assert 'Loading work.' not in log and 'RESULT:' not in log
    result['status']='MODELSIM_BATCH_TOOL_STARTUP_PASS_NO_HDL'
    print(result['status'])
except Exception as exc:
    result.update(status='MODELSIM_BATCH_TOOL_STARTUP_STOPPED',error=f'{type(exc).__name__}: {exc}')
    raise
finally:
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
