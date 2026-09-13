import re, os

# ---- 按 Pango GTP_DRM36K_E1 模型的真实读取规则解码 ----
# mem[cnt] = INIT_xx[cnt*9 +: 9]          (cnt = 0..31)
# 32bit 字 W 读自 {mem[4W+3][7:0], mem[4W+2][7:0], mem[4W+1][7:0], mem[4W][7:0]}
# word index = (INIT 序号 * 8) + k ,  k = 0..7

IPF = r"D:\riscv\RISCV\ipcore\inst_rom\rtl\inst_rom_init_param.v"
DAT = r"D:\riscv\tbtb\rom_test.dat"
OUT = r"D:\riscv\RISCV\.workbuddy\sim_rom\decode_report.txt"

vals = {}
txt = open(IPF, "r", encoding="utf-8", errors="replace").read()
for m in re.finditer(r"localparam\s+INIT_([0-9A-F]{2})_0_0\s*=\s*288'h([0-9a-fA-F]+)", txt):
    vals[int(m.group(1), 16)] = int(m.group(2), 16)

words = {}
for nn, V in vals.items():
    slots = [(V >> (9 * j)) & 0x1FF for j in range(32)]
    for k in range(8):
        w = ((slots[4*k+3] & 0xFF) << 24) | ((slots[4*k+2] & 0xFF) << 16) \
          | ((slots[4*k+1] & 0xFF) << 8)  | (slots[4*k] & 0xFF)
        words[nn * 8 + k] = w

dat = []
with open(DAT, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        line = line.strip()
        if line == "":
            continue
        dat.append(int(line, 16))

lines = []
lines.append("INIT_xx 参数个数 = %d" % len(vals))
lines.append("解码出字数       = %d" % len(words))
lines.append("rom_test.dat 字数= %d" % len(dat))
lines.append("")
lines.append(" addr | IP 固化   | rom_test.dat | 判定")
lines.append("------+-----------+--------------+-----")
bad = 0
for a in range(min(len(dat), len(words))):
    same = (words.get(a, -1) == dat[a])
    if not same:
        bad += 1
    if a < 20 or not same:
        lines.append("%5d | 0x%08X | 0x%08X   | %s" % (a, words.get(a, 0), dat[a], "OK" if same else "DIFF"))

lines.append("")
lines.append("全部 %d 个地址中,不一致 %d 个" % (min(len(dat), len(words)), bad))
lines.append("")
lines.append("---- 三种解码口径对地址 0 的结果对照 ----")
V0 = vals[0]
lines.append("原始 288bit 值          : 0x%072X" % V0)
lines.append("低 36bit 槽(直接截 32bit): 0x%08X   <-- 旧文档用的口径(错)" % (V0 & 0xFFFFFFFFF))
lines.append("低 32bit 直接截取        : 0x%08X   <-- 也是错的(落在一个 36bit 槽的中间)" % (V0 & 0xFFFFFFFF))
lines.append("按 mem_read_a 规则解码   : 0x%08X   <-- 就是 DUT 实际读出的值" % words[0])
lines.append("rom_test.dat[0]          : 0x%08X" % dat[0])

open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("\n".join(lines))
