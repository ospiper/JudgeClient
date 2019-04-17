import _judger
import hashlib
import json
import os
import re
import uuid
from multiprocessing import Pool

import psutil

from config import TEST_CASE_DIR, JUDGER_WORKSPACE_BASE, JUDGER_RUN_LOG_PATH, RUN_GROUP_GID, RUN_USER_UID, SPJ_EXE_DIR, RUN_GROUP_GID
from exception import JudgeClientError
# from utils import ProblemIOMode

SPJ_WA = 1
SPJ_AC = 0
SPJ_ERROR = -1

"""
JSON Data Structure
{
type: 'io' | 'spj' | 'interactive'
subtasks: [
    {
        subtask_id: Number
        type: 'sum' | 'mul'
        score: Number
        cases: [
            {
                case_id: Number
                input_size: Number
                input_name: String
                output_size: Number
                output_name: String
                output_md5: String
            }
        ]
    }
]
}

Return Data Structure
{
task_id: String
problem_id: String
user_id: String
cpu_time: Number
peak_memory: Number
result: Number
error: Number
message: String
subtasks: [
    {
        subtask_id: Number
        type: 'sum' | 'mul'
        score: Number
        cases: [
            {
                case_id: Number
                cpu_time: Number (ms)
                real_time: Number
                memory: Number (Bytes)
                signal: Number
                exit_code: Number
                result: Number
                error: Number
            }
        ]
    }
]

"""

class JudgeClient:
    def __init__(self, run_config, exe_path, max_cpu_time, max_memory, problem_id,
                 runner_id, output=False):
        self.run_config = run_config
        self.problem_id = problem_id
        self.runner_id = runner_id
        self.exe_path = exe_path
        self.max_cpu_time = max_cpu_time
        self.max_memory = max_memory
        self.max_real_time = self.max_cpu_time * 3
        self.task_path = os.path.join(TEST_CASE_DIR, problem_id)
        self.judge_info = self.load_judge_info(problem_id)
        self.runner_path = os.path.join(JUDGER_WORKSPACE_BASE, self.runner_id)
        self.output = output
        print('[JUDGE INFO]')
        print(self.judge_info)

    def load_judge_info(self, problem_id):
        try:
            with open(os.path.join(self.task_path, 'info.json')) as f:
                return json.load(f)
        except IOError:
            raise JudgeClientError("Test case not found: " + problem_id)
        except ValueError:
            raise JudgeClientError("Bad test case config")

    def handle_output(self, output):
        return '\n'.join([x.rstrip() for x in output.rstrip().replace('\r\n', '\n').replace('\r', '\n').split('\n')])

    def compare_output(self, case):
        user_output_file = os.path.join(self.runner_path, case['output_name'])
        with open(user_output_file, "r", encoding="utf-8") as f:
            content = f.read()
        output_md5 = hashlib.md5(self.handle_output(content).encode("utf-8")).hexdigest()
        return output_md5 == case['output_md5']

    def judge_case(self, case):
        """
        task_path: /test_case/problem_id
        runner_path: /judger/run/runner_id
        {
            case_id: Number
            input_size: Number
            input_name: String
            output_size: Number
            output_name: String
            output_md5: String
        }
        """
        in_file = os.path.join(self.task_path, case['input_name'])
        user_output_file = os.path.join(self.runner_path, case['output_name'])
        command = self.run_config["command"].format(exe_path=self.exe_path, exe_dir=os.path.dirname(self.exe_path),
                                                    max_memory=int(self.max_memory / 1024)).split(" ")
        env = ["PATH=" + os.environ.get("PATH", "")] + self.run_config.get("env", [])
        seccomp_rule = self.run_config["seccomp_rule"]

        kwargs = {"input_path": in_file, "output_path": user_output_file, "error_path": user_output_file}
        case_result = _judger.run(max_cpu_time=self.max_cpu_time,
                                  max_real_time=self.max_real_time,
                                  max_memory=self.max_memory,
                                  max_stack=128 * 1024 * 1024,
                                  max_output_size=max(case.get("output_size", 0) * 2, 1024 * 1024 * 16),
                                  max_process_number=_judger.UNLIMITED,
                                  exe_path=command[0],
                                  args=command[1::],
                                  env=env,
                                  log_path=JUDGER_RUN_LOG_PATH,
                                  seccomp_rule_name=seccomp_rule,
                                  uid=RUN_USER_UID,
                                  gid=RUN_GROUP_GID,
                                  memory_limit_check_only=self.run_config.get("memory_limit_check_only", 0),
                                  **kwargs)

        if case_result["result"] == _judger.RESULT_SUCCESS:
            if os.path.exists(user_output_file):
                result = self.compare_output(case)
                if result is not True:
                    case_result['result'] = _judger.RESULT_WRONG_ANSWER
            else:
                case_result['result'] = _judger.RESULT_WRONG_ANSWER
        return case_result

    def judge_subtask(self, subtask):
        subtask_result = {
            'subtask_id': subtask['subtask_id'],
            'type': subtask['type'],
            'score': subtask['score'],
            'cases': []
        }
        for case in subtask['cases']:
            subtask_result['cases'].append(self.judge_case(case))
        return subtask_result

    def judge(self):
        ret = []
        for subtask in self.judge_info['subtasks']:
            ret.append(self.judge_subtask(subtask))
        return ret

    """
    def __getstate__(self):
        # http://stackoverflow.com/questions/25382455/python-notimplementederror-pool-objects-cannot-be-passed-between-processes
        self_dict = self.__dict__.copy()
        del self_dict["_pool"]
        return self_dict
    """