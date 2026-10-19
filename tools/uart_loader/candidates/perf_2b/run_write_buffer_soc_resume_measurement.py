"""Same frozen P300/V300 transport; use Task027 SoC repair evidence without a bitstream gate."""
import run_write_buffer_measurement as transport
transport.GATE=transport.ROOT/'sim/mini_board_migration/build/ds_mini_write_buffer_soc_resume_20261013_a/codex_review.json'
if __name__=='__main__':transport.main()
