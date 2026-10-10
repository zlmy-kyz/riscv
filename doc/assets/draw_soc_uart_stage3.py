"""Render the verified stage-3 SoC structure as editable SVG and PNG.

Run: python doc/assets/draw_soc_uart_stage3.py
Requires Pillow and the Windows Microsoft YaHei font; no RTL is modified.
"""
from html import escape
from pathlib import Path
import math

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
STEM = "SoC结构图_UART阶段3_2026-10-05"
WIDTH, HEIGHT, SCALE = 1800, 1580, 2
FONT = Path("C:/Windows/Fonts/msyh.ttc")
BOLD = Path("C:/Windows/Fonts/msyhbd.ttc")
INK, BLUE, GREEN, RED = "#18334e", "#306acb", "#13836c", "#c44b59"
img = Image.new("RGB", (WIDTH * SCALE, HEIGHT * SCALE), "white")
draw = ImageDraw.Draw(img)
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
       '<title>当前 RISC-V SoC：UART MMIO 阶段 3</title>',
       '<desc>board_top、soc_ddr3_top、soc_top 层次；独立指令和数据互连、ROM、RAM、MMIO、UART、共享 DDR 桥、DDR IP 与板外 DDR3。UART RX 固定为高，TX 未引出。</desc>',
       '<rect width="100%" height="100%" fill="white"/>']


def text(x, y, value, size=22, color=INK, bold=False, anchor="middle"):
    font = ImageFont.truetype(str(BOLD if bold else FONT), size * SCALE)
    draw.text((x * SCALE, y * SCALE), value, font=font, fill=color,
              anchor="mm" if anchor == "middle" else "lm")
    svg.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" dominant-baseline="middle" '
               f'font-family="Microsoft YaHei, Noto Sans CJK SC, sans-serif" font-size="{size}" '
               f'font-weight="{700 if bold else 400}" fill="{color}">{escape(value)}</text>')


def rect(x, y, w, h, fill, stroke, radius=16, line=2):
    draw.rounded_rectangle(tuple(v * SCALE for v in (x, y, x + w, y + h)),
                           radius=radius * SCALE, fill=fill, outline=stroke, width=line * SCALE)
    svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
               f'fill="{fill}" stroke="{stroke}" stroke-width="{line}"/>')


def group(x, y, w, h, title, fill, stroke):
    rect(x, y, w, h, fill, stroke, 20)
    text(x + 22, y + 24, title, 23, stroke, True, "start")


def node(x, y, w, h, lines, fill="white", stroke="#91a8c2"):
    rect(x, y, w, h, fill, stroke)
    total = sum(size + 8 for _, size in lines) - 8
    cursor = y + (h - total) / 2
    for index, (label, size) in enumerate(lines):
        text(x + w / 2, cursor + size / 2, label, size, bold=index == 0)
        cursor += size + 8


def arrow(points, color=BLUE, dashed=False, width=3):
    scaled = [(x * SCALE, y * SCALE) for x, y in points]
    if not dashed:
        draw.line(scaled, fill=color, width=width * SCALE, joint="curve")
    else:
        for (x1, y1), (x2, y2) in zip(points, points[1:]):
            length = math.hypot(x2 - x1, y2 - y1)
            for pos in range(0, math.ceil(length), 16):
                end = min(pos + 9, length)
                draw.line([(int((x1 + (x2-x1)*p/length)*SCALE),
                            int((y1 + (y2-y1)*p/length)*SCALE)) for p in (pos, end)],
                          fill=color, width=width * SCALE)
    x, y = points[-1]
    px, py = points[-2]
    angle = math.atan2(y - py, x - px)
    head = [(x, y), (x - 13 * math.cos(angle) + 6 * math.sin(angle),
                     y - 13 * math.sin(angle) - 6 * math.cos(angle)),
                    (x - 13 * math.cos(angle) - 6 * math.sin(angle),
                     y - 13 * math.sin(angle) + 6 * math.cos(angle))]
    draw.polygon([(int(a*SCALE), int(b*SCALE)) for a, b in head], fill=color)
    coordinates = " ".join(f"{a},{b}" for a, b in points)
    svg.append(f'<polyline points="{coordinates}" fill="none" stroke="{color}" '
               f'stroke-width="{width}" stroke-linejoin="round" '
               + ('stroke-dasharray="9 7" ' if dashed else '') + '/>')
    svg.append(f'<polygon points="{" ".join(f"{a},{b}" for a,b in head)}" fill="{color}"/>')


text(900, 45, "当前 RISC-V SoC 结构 · UART MMIO 阶段 3", 34, bold=True)
text(900, 88, "单核 RV32I · 指令/数据分离 · DDR 用户时钟 93.75 MHz · UART 115200 8N1", 22)
for x, color, dashed, label in [(95, BLUE, False, "访问 / 数据路径（响应省略）"),
                              (635, GREEN, True, "时钟"), (845, RED, True, "复位控制")]:
    arrow([(x, 123), (x + 75, 123)], color, dashed)
    text(x + 92, 123, label, 19, color, anchor="start")

group(40, 150, 1720, 1260, "board_top · 当前 PDS 设计顶层 / FPGA 板级边界", "#f8fafc", "#70879e")
group(70, 325, 1660, 1010, "soc_ddr3_top · SoC + DDR IP + 复位同步 + LED", "#f5f8fc", "#70879e")
group(100, 385, 1350, 720, "soc_top · CPU、互连、存储与外设", "#edf5ff", BLUE)
text(900, 409, "统一时钟域：core_clk = 93.75 MHz", 21, GREEN, anchor="start")
group(885, 800, 490, 275, "uart_mmio · 内部轮询外设", "#fff6e9", "#b77d22")

# Clock and reset use the existing DDR core domain. No board UART is implied.
arrow([(350, 230), (405, 230)], GREEN, True)
arrow([(680, 230), (730, 230)], GREEN, True)
arrow([(70, 230), (55, 230), (55, 1205), (190, 1205)], GREEN, True)
arrow([(220, 1160), (220, 1135), (85, 1135), (85, 465), (100, 465)], GREEN, True)
arrow([(1035, 270), (1035, 300), (1480, 300), (1480, 480), (1500, 480)], RED, True)
arrow([(1500, 455), (1450, 455)], RED, True)
arrow([(1035, 270), (1035, 300), (1480, 300), (1480, 1215), (1150, 1215)], RED, True)
arrow([(1150, 1190), (1460, 1190), (1460, 535), (1500, 535)], RED, True)

# Real instruction/data interconnect paths; the DDR bridge is shared.
arrow([(620, 520), (620, 542), (340, 542), (340, 565)])
arrow([(730, 520), (730, 542), (1045, 542), (1045, 565)])
arrow([(340, 635), (340, 690)])
arrow([(340, 760), (340, 810)])
arrow([(490, 600), (515, 600), (515, 970)])
arrow([(1045, 635), (1045, 665), (695, 665), (695, 690)])
arrow([(1135, 635), (1135, 690)])
arrow([(695, 760), (695, 810)])
arrow([(865, 635), (865, 1015), (835, 1015)])
arrow([(1260, 600), (1400, 600), (1400, 883), (1345, 883)])
arrow([(515, 1060), (515, 1160)])
arrow([(1375, 733), (1500, 733)])
arrow([(985, 916), (985, 965)])
arrow([(1200, 995), (1225, 995)])
arrow([(1290, 965), (1290, 916)])
arrow([(670, 1255), (670, 1435)])

node(70, 190, 280, 80, [("GTP_INBUFDS", 23), ("125 MHz 差分参考输入", 20)])
node(405, 190, 275, 80, [("GTP_CLKBUFG", 23), ("KEY0 消抖参考时钟", 20)])
node(730, 190, 340, 80, [("reset_button_debounce", 21), ("KEY0：按下复位 / 释放稳定 20 ms", 17)])
node(1150, 190, 580, 80, [("阶段 3 边界：UART 仅在 SoC 内部接入", 23), ("RX 接高 / TX 未引出 · 无板级 UART 引脚 / 中断", 18)], "#fff6e9", "#d4a75d")
node(1500, 430, 195, 150, [("复位释放同步", 21), ("DDR ready && lock", 16), ("core_clk 两拍", 18), ("输出 soc_resetn", 17)], "#fff1f2", "#d28a93")
node(500, 430, 350, 90, [("mycpu_sync · RV32I CPU", 24), ("五级流水：IF / ID / EX / MEM / WB", 18)], "#dceaff", BLUE)
node(190, 565, 300, 70, [("inst_bus_interconnect", 21), ("指令地址译码：ROM / DDR", 18)])
node(830, 565, 430, 70, [("data_bus_interconnect", 23), ("数据地址译码：RAM / MMIO / UART / DDR", 18)])
node(190, 690, 300, 70, [("inst_bram_adapter", 22), ("请求响应 → 同步 ROM 端口", 18)])
node(540, 690, 310, 70, [("data_bram_adapter", 22), ("请求响应 → RAM / 字节使能", 18)])
node(190, 810, 300, 95, [("inst_rom · 16 KiB", 24), ("指令总线上的启动 ROM", 18), ("0x00000000–0x00003FFF", 17)], "#e8f3ed")
node(540, 810, 310, 95, [("data_ram · 16 KiB", 24), ("数据 RAM / DDR 程序装载源", 18), ("0x00000000–0x00003FFF", 17)], "#e8f3ed")
node(895, 690, 480, 85, [("simple_mmio", 24), ("0x10000000–0x10000FFF", 18), ("SCRATCH / ID / CYCLE / STATUS / TEST_STATUS", 16)])
node(915, 850, 430, 66, [("MMIO 寄存器 / 请求响应", 23), ("0x10001000–0x1000100F · TX/RX/STATUS/CONTROL", 16)], "#fffdf7", "#d4a75d")
node(915, 965, 145, 60, [("uart_tx", 22), ("TX 未引出", 18)], "white", "#d4a75d")
node(1085, 965, 115, 60, [("uart_rx", 20), ("RX 固定 1", 16)], "white", "#d4a75d")
node(1225, 965, 125, 60, [("RX FIFO", 20), ("16 字节", 17)], "white", "#d4a75d")
node(190, 970, 645, 90, [("dual_sram_to_pango_ddr_bridge", 25), ("指令/数据共享 · 单拍事务 · 同时请求数据优先", 19), ("DDR 窗口：0x40000000–0x5FFFFFFF", 18)], "#e5edfa", BLUE)
node(1500, 690, 195, 100, [("soc_ddr3_leds", 19), ("心跳 / DDR 就绪", 18), ("自检 PASS/FAIL", 18)])
node(190, 1160, 960, 95, [("ddr3 · Pango 控制器 + PHY", 25), ("ips2l_mcdq_wrapper_v1_2b / ddr3_ddrphy_top", 20), ("128-bit AXI-like 用户口 · 750 Mb/s · 输出 core_clk = 93.75 MHz", 19)], "#e6f4f0", GREEN)
node(190, 1435, 960, 80, [("板外 x16 DDR3 芯片", 25), ("通过 FPGA DDR3 物理引脚连接", 20)], "#f1f4f8", "#70879e")

text(1330, 455, "soc_resetn", 18, RED, anchor="start")
text(1500, 910, "ready / lock", 17, RED, anchor="start")
text(1492, 1060, "key_resetn", 18, RED, anchor="start")
text(70, 1185, "125 MHz 参考", 16, GREEN, anchor="start")
text(105, 1115, "core_clk", 18, GREEN, anchor="start")
text(530, 940, "DDR 取指", 18, BLUE, anchor="start")
text(780, 940, "DDR 数据", 18, BLUE, anchor="start")
text(545, 1120, "32-bit CPU 访问 / 128-bit DDR 用户拍", 19, BLUE, anchor="start")
text(1385, 716, "selftest_status", 16, BLUE, anchor="start")
text(1320, 943, "读 / pop", 15, BLUE)
text(1125, 1048, "115200 8N1 · 814 clk/bit · 未接板级引脚 / 中断", 17, "#94691e")
text(1310, 1360, "ROM 与 RAM 分挂两条总线，可同基址。", 20)
text(1310, 1386, "DDR 由两条总线共同访问。", 20)
text(900, 1550, "核对：2026-10-05 · 按当前工作树 RTL 绘制 · UART 仿真可使用 soc_top TX/RX，板级 RX 接高、TX 未引出", 18, "#596f83")

svg.append("</svg>")
(OUT / f"{STEM}.svg").write_text("\n".join(svg) + "\n", encoding="utf-8")
img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS).save(OUT / f"{STEM}.png")
print(OUT / f"{STEM}.svg")
print(OUT / f"{STEM}.png")
