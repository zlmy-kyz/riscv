def R(f3, f7, rd, rs1, rs2, op):
    return (f7 << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op

def I(imm, rd, rs1, f3, op):
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op

def S(imm, rs2, rs1, f3, op):
    return (((imm >> 5) & 0x7F) << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | ((imm & 0x1F) << 7) | op

def U(imm20, rd, op):
    return (imm20 << 12) | (rd << 7) | op

prog = [
    ("lui   x10, 0x12345", U(0x12345, 10, 0x37)),
    ("auipc x11, 0x1",     U(0x00001, 11, 0x17)),
    ("addi  x12, x0, -1",  I(0xFFF, 12, 0, 0b000, 0x13)),
    ("addi  x13, x12, 1",  I(0x001, 13, 12, 0b000, 0x13)),
    ("slli  x14, x12, 4",  I(0x004, 14, 12, 0b001, 0x13)),   # 高 7 位 0 + shamt 4
    ("srli  x15, x12, 28", I(0x01C, 15, 12, 0b101, 0x13)),   # 高 7 位 0 + shamt 28
    ("sw    x14, 8(x0)",   S(8, 14, 0, 0b010, 0x23)),
    ("lw    x16, 4(x0)",   I(4, 16, 0, 0b010, 0x03)),
]

for i, (asm, v) in enumerate(prog):
    print("mem[%d] = 32'h%08X;  // 0x%02X  %s" % (i, v, i * 4, asm))

print()
print("exp checks:")
print("x10 = 0x12345000 ; x11 = 0x1004 ; x12 = 0xFFFFFFFF ; x13 = 0x00000000")
print("x14 = 0xFFFFFFF0 ; x15 = 0x0000000F ; sw addr = 8 ; lw addr = 4")
