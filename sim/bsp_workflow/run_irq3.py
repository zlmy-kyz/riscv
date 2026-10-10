"""BSP UART IRQ test with application RX retirement matching enabled after DDR entry."""
from pathlib import Path
import sys
import run
assert '--application' in sys.argv and sys.argv[sys.argv.index('--application')+1]=='irq_probe'
run.HERE=Path(__file__).resolve().parent/'irq3'
run.main()
