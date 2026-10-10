"""Unified simulation entry, including BSP IRQ and timer-wrap directed checks."""
from pathlib import Path
import re,sys
import run
if '--build-tag' in sys.argv:
    i=sys.argv.index('--build-tag');tag=sys.argv[i+1];assert re.fullmatch('[a-z0-9_-]+',tag)
    del sys.argv[i:i+2]
    run.manifest=lambda name:run.ROOT/f'tests/bsp_workflow/build_versions/{tag}/{name}/manifest.json'
if '--timer-wrap' in sys.argv:
    sys.argv.remove('--timer-wrap');assert sys.argv[sys.argv.index('--application')+1]=='hello'
    run.HERE=Path(__file__).resolve().parent/'timer_wrap'
elif sys.argv[sys.argv.index('--application')+1]=='irq_probe':
    run.HERE=Path(__file__).resolve().parent/'irq3'
run.main()
