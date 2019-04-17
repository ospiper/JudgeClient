import dramatiq
import requests
import json
import uuid
import os
import shutil
from compiler import Compiler
from JudgeClient import JudgeClient
from config import TEST_CASE_DIR, JUDGER_WORKSPACE_BASE


"""
Request Data Structure
{
judge_id: String
problem_id: String
user_id: String
code: String
compiler: String
max_cpu_time: Number
max_memory: Number
compiler_config: {
    src_name: String
    exe_name: String
    max_cpu_time: Number,
    max_real_time: Number,
    max_memory: Number,
    compile_command: String
}
runner_config: {
    command: String
    seccomp_rule: String
    env: []
}
}
"""
@dramatiq.actor
def judge(judge_id,
          problem_id,
          user_id,
          code,
          compiler,
          max_cpu_time,
          max_memory,
          compiler_config,
          runner_config):
    try:
        # ARGS CHECK HERE
        # PREPARE FOR JUDGING
        runner_id = str(uuid.uuid4().hex)
        runner_dir = os.path.join(JUDGER_WORKSPACE_BASE, runner_id)
        os.makedirs(runner_dir)
        src_path = os.path.join(runner_dir, compiler_config['src_name'])
        with open(src_path, 'w', encoding='utf-8') as code:
            code.write(code)
        # COMPILE

        exe_path = Compiler.compile(compiler_config, src_path, runner_dir)
        # CHECK COMPILE ERROR
        client = JudgeClient(
            run_config=runner_config,
            exe_path=exe_path,
            max_cpu_time=max_cpu_time,
            max_memory=max_memory,
            problem_id=problem_id,
            runner_id=runner_id
        )
        result = client.judge()
        # PROCEED RESULT HERE

        # CLEAN-UP
        shutil.rmtree(runner_dir)
        print("[JUDGE TASK RESULT]")
        print(json.dumps(result))
    except IOError:
        print("FILE NOT FOUND")
        pass
    except ValueError:
        print("BAD JUDGE TASK INFO")
        pass
