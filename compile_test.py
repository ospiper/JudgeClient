import dramatiq
import requests
import json
import uuid
import os
import shutil
from compiler import Compiler
from JudgeClient import JudgeClient
from judger_config import TEST_CASE_DIR, JUDGER_WORKSPACE_BASE

runner_id = '00001'
compiler_config = {
        "src_name": "main.c",
        "exe_name": "main",
        "max_cpu_time": 3000,
        "max_memory": 512 * 1024 * 1024,
        "compile_command": "/usr/bin/gcc -DONLINE_JUDGE -O2 -w -fmax-errors=3 -std=c99 {src_path} -lm -o {exe_path}",
    }
code = r"""
    #include <stdio.h>
    int main(){
        int a, b;
        scanf("%d%d", &a, &b);
        printf("%d\n", a+b);
        return 0;
    }
    """


def clean_up(path):
    print("CLEANING UP ", path)
    shutil.rmtree(path)


if __name__ == '__main__':
    print(code)
    runner_dir = os.path.join(JUDGER_WORKSPACE_BASE, runner_id)
    if os.path.exists(runner_dir):
        clean_up(runner_dir)
    os.makedirs(runner_dir)
    src_path = os.path.join(runner_dir, compiler_config['src_name'])
    with open(src_path, 'w', encoding='utf-8') as code_file:
        code_file.write(code)
    exe_path = Compiler.compile(compiler_config, src_path, runner_dir)
    print(exe_path)
