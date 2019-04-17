import dramatiq
import requests
import json
import uuid
import os
import shutil
from compiler import Compiler
from JudgeClient import JudgeClient
from judger_config import TEST_CASE_DIR, JUDGER_WORKSPACE_BASE
from judger import judge


task_id = 'judge_test_id'
problem_id = 'test'
user_id = 'user_test_id'
code = r"""
              #include <stdio.h>
              int main(){
                  int a, b;
                  scanf("%d%d", &a, &b);
                  printf("%d\n", 3);
                  return 0;
              }
        """
max_cpu_time = 1000
max_memory = 128 * 1024 * 1024
compiler_config = {
        "src_name": "main.c",
        "exe_name": "main",
        "max_cpu_time": 3000,
        "max_memory": 512 * 1024 * 1024,
        "compile_command": "/usr/bin/gcc -DONLINE_JUDGE -O2 -w -fmax-errors=3 -std=c99 {src_path} -lm -o {exe_path}",
    }
runner_config = {
        "command": "{exe_path}",
        "seccomp_rule": "c_cpp",
        "env": []
    }

if __name__ == '__main__':
    result = judge(task_id=task_id,
                   problem_id=problem_id,
                   user_id=user_id,
                   code=code,
                   max_cpu_time=max_cpu_time,
                   max_memory=max_memory,
                   compiler_config=compiler_config,
                   runner_config=runner_config)

