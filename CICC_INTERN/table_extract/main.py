# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import warnings
import argparse
warnings.filterwarnings("ignore")

def run_script(script_name, args_list=None):
    print(f"\n========================================")
    print(f" 正在执行：{script_name}")
    print(f"========================================\n")
    
    cmd = [sys.executable, script_name]
    if args_list:
        cmd.extend(args_list)
    
    result = subprocess.run(cmd, shell=False)
    return result.returncode == 0

def main():
    parser = argparse.ArgumentParser(description="表格处理主程序（支持批量）")
    parser.add_argument("--func", choices=["screenshot", "classify", "all"], default="all")
    # 批量模式：传入多个文件名，用空格分隔
    parser.add_argument("--filenames", nargs="+", help="批量文件名：201 202 203 cmb icbc", required=True)
    args = parser.parse_args()

    print(f"🚀 开始批量处理表格，共 {len(args.filenames)} 个文件")
    
    # 批量循环
    for fname in args.filenames:
        print(f"\n==================================================")
        print(f"               处理文件：{fname}")
        print(f"==================================================")
        
        if args.func in ["screenshot", "all"]:
            # run_script("html_extract_table.py", ["--filename", fname])
            run_script("pdf_extract_tables.py", ["--filename", fname])
        
        if args.func in ["classify", "all"]:
            run_script("json_table_classify.py", ["--filename", fname])
    
    print(f"\n🎉 所有文件批量处理完成！")

if __name__ == "__main__":
    main()