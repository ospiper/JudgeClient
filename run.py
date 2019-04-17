
import json
from JudgeClient import JudgeClient

if __name__ == '__main__':
    client = JudgeClient(
        run_config={
            "command": "{exe_path}",
            "seccomp_rule": "c_cpp",
            "env": []
        },
        exe_path="/judger/run/00000/main.o",
        max_cpu_time=3000,
        max_memory=1048576,
        problem_id='test',
        runner_id='00000'
    )
    result = client.judge()
    print("[JUDGE RESULT]")
    print(json.dumps(result))
