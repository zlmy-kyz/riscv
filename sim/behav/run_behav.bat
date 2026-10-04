@echo off
set bin_path=D:/modelsim/win64pe
cd D:/riscv/RISCV/sim
call "%bin_path%/modelsim"   -do "do {D:/riscv/RISCV/sim/board_main_selftest/compile.tcl};do {D:/riscv/RISCV/sim/board_main_selftest/run.tcl}" -l D:/riscv/RISCV/sim/behav/run_behav_simulate.log
if "%errorlevel%"=="1" goto END
if "%errorlevel%"=="0" goto SUCCESS
:END
exit 1
:SUCCESS
exit 0
