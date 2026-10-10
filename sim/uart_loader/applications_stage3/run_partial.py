"""60-iteration startup integration only; drain accepted transactions at test end."""
from pathlib import Path
import sys
import run

assert '--application' in sys.argv
name=sys.argv[sys.argv.index('--application')+1]
assert name in ('performance_60','validation_60')
run.HERE=Path(__file__).resolve().parent/'partial'
run.main()
