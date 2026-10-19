"""Same frozen P300/V300 tool, bound to Task031's fresh include-fix gate."""
import run_write_buffer_turnover_measurement as original

original.GATE = original.ROOT / 'sim/write_buffer_turnover/build/ds_write_buffer_turnover_init_resume_20261014_a/codex_review.json'
verify = original.verify


if __name__ == '__main__':
    original.main()
