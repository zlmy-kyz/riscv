"""Frozen P300/V300; gate is Codex's offline IRQ-contract evidence closure."""
import run_write_buffer_turnover_measurement as original

original.GATE = original.ROOT / 'sim/write_buffer_turnover/build/codex_irq_contract_closure_20261014_a/codex_review.json'
verify = original.verify


if __name__ == '__main__':
    original.main()
