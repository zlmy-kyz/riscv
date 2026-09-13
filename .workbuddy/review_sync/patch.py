import io, os, sys

SRC = r"D:\riscv\RISCV\myriscv\mycpu_sync.v"
DST = r"D:\riscv\RISCV\.workbuddy\review_sync\mycpu_sync_fixed.v"

raw = open(SRC, "rb").read()
enc = "utf-8"
try:
    txt = raw.decode("utf-8")
except UnicodeDecodeError:
    enc = "gbk"
    txt = raw.decode("gbk")
print("source encoding guess:", enc, "size:", len(raw))

orig = txt
# 1) valid 拼写错误 -> 统一成 vaild
txt = txt.replace("{4{valid}}", "{4{vaild}}")
txt = txt.replace("gf_we & valid", "gf_we & vaild")
# 2) regfile 例化里多出的 rst_n 端口(该 regfile 没有这个端口)
txt = txt.replace("        .waddr (rf_waddr), .we(rf_we), .rst_n(resetn),\n",
                  "        .waddr (rf_waddr), .we(rf_we),\n")

open(DST, "w", encoding="utf-8", newline="\n").write(txt)
print("wrote:", DST)
print("changed:", txt != orig)
