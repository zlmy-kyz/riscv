#!/usr/bin/env python3
import os
import subprocess
import glob
 
def batch_generate_bin():
    # 设置工具链路径
    objcopy = "riscv64-unknown-elf-objcopy"
 
    # 检查 objcopy 是否可用
    try:
        subprocess.run([objcopy, "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print(f"错误: 找不到 {objcopy}，请检查工具链路径")
        return False
 
    # 创建输出目录 - 使用 ../bin
    output_dir = "../bin"
    os.makedirs(output_dir, exist_ok=True)
    
    # 查找所有 rv32ui-p-* 文件（无后缀）
    test_files = [f for f in glob.glob("rv32ui-p-*") if os.path.isfile(f)]
    
    # 过滤掉可能误匹配的文件
    test_files = [f for f in test_files if not f.endswith(('.bin', '.dump', '.S', '.s', '.c'))]
    
    if not test_files:
        print("未找到任何 rv32ui-p-* 测试文件")
        return False
    
    success_count = 0
    failed_files = []
    
    print(f"找到 {len(test_files)} 个测试文件")
    
    for test_file in test_files:
        # 生成 bin 文件名 - 使用 ../bin 目录
        bin_file = os.path.join(output_dir, f"{test_file}.bin")
        
        try:
            # 执行转换命令
            result = subprocess.run(
                [objcopy, "-O", "binary", test_file, bin_file],
                capture_output=True,
                text=True,
                check=True
            )
            
            if os.path.exists(bin_file) and os.path.getsize(bin_file) > 0:
                success_count += 1
            else:
                print(f"  ✗ 生成的文件为空或不存在")
                failed_files.append(test_file)
        except subprocess.CalledProcessError as e:
            print(f"  ✗ 转换失败: {e.stderr.strip()}")
            failed_files.append(test_file)
    
    # 输出总结
    print("\n" + "="*50)
    print(f"批量转换完成！")
    print(f"成功: {success_count}/{len(test_files)}")
    
    if failed_files:
        print(f"失败的文件:")
        for f in failed_files:
            print(f"  - {f}")
    
    return len(failed_files) == 0
 
if __name__ == "__main__":
    batch_generate_bin()