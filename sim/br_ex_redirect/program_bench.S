# Taken-branch throughput benchmark.
# 1000 iterations, each with one taken conditional branch, so the per-branch
# redirect cost can be compared between RTL revisions with the same testbench.
# dmem[8] = 1000 marks completion; the TB prints BENCH_DONE cycles=<n>.
        addi x1, x0, 0
        addi x2, x0, 1000
        addi x3, x0, 1
        addi x4, x0, 2
        addi x5, x0, 3
        addi x6, x0, 4
BENCH:  addi x1, x1, 1
        add  x3, x3, x4
        xor  x5, x5, x6
        blt  x1, x2, BENCH
        sw   x1, 32(x0)
DONE:   j    DONE
