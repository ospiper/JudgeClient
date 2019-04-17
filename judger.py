import dramatiq
import requests
import json
import uuid
import os
import shutil
from compiler import Compiler
from JudgeClient import JudgeClient
from judger_config import TEST_CASE_DIR, JUDGER_WORKSPACE_BASE
from dramatiq.brokers.rabbitmq import RabbitmqBroker
from exception import CompileError
import _judger
from service_config import BROKER_URL, CALLBACK_URL, TOKEN

rabbitmq_broker = RabbitmqBroker(url=BROKER_URL)
dramatiq.set_broker(rabbitmq_broker)
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
def judge(task_id,
          problem_id,
          user_id,
          code,
          max_cpu_time,
          max_memory,
          compiler_config,
          runner_config):
    runner_id = str(uuid.uuid4().hex)
    runner_dir = os.path.join(JUDGER_WORKSPACE_BASE, runner_id)
    task_result = {
        'task_id': task_id,
        'problem_id': problem_id,
        'user_id': user_id,
        'cpu_time': 0,
        'real_time': 0,
        'peak_memory': 0,
        'result': 0,
        'error': 0,
        'score': 0,
        'message': None,
        'subtasks': []
    }
    try:
        # ARGS CHECK HERE
        # PREPARE FOR JUDGING

        print("[RUNNER]", runner_id)
        os.makedirs(runner_dir)
        src_path = os.path.join(runner_dir, compiler_config['src_name'])
        with open(src_path, 'w', encoding='utf-8') as code_file:
            code_file.write(code)
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
        subtasks_result = client.judge()
        # PROCEED RESULT HERE
        """
        JudgeClient returns:
        [
            {
                "subtask_id":1,
                "type":"sum",
                "score":100,
                "cases":[
                    {
                        "cpu_time":0,
                        "real_time":2,
                        "memory":1712128,
                        "signal":0,
                        "exit_code":0,
                        "error":0,
                        "result":0
                    }
                ]
            }
        ]
        """
        for subtask in subtasks_result:
            subtask_type = subtask['type']
            count_cases = len(subtask['cases'])
            total_score = subtask['score']
            ac_cases = 0
            for case in subtask['cases']:
                task_result['cpu_time'] += case['cpu_time']
                task_result['real_time'] += case['real_time']
                if case['result'] != _judger.RESULT_SUCCESS:
                    task_result['result'] = case['result']
                if case['error'] != 0:
                    task_result['error'] = case['error']
                if case['memory'] > task_result['peak_memory']:
                    task_result['peak_memory'] = case['memory']
                if case['result'] == _judger.RESULT_SUCCESS:
                    ac_cases += 1
            if subtask_type == 'sum':
                score = total_score * (ac_cases / count_cases)
            elif subtask_type == 'mul':
                score = total_score if count_cases == ac_cases else 0
            else:
                score = 0
            subtask['score'] = score
            task_result['subtasks'].append(subtask)
    except IOError:
        task_result['result'] = _judger.RESULT_SYSTEM_ERROR
        task_result['message'] = 'Code file not found'
        pass
    except ValueError:
        task_result['result'] = _judger.RESULT_SYSTEM_ERROR
        task_result['message'] = 'Bad judge task info'
        pass
    except CompileError as ce:
        task_result['result'] = _judger.RESULT_COMPILE_ERROR
        task_result['message'] = ce.message
        pass

    # CLEAN-UP
    shutil.rmtree(runner_dir)
    print("[JUDGE TASK RESULT]")
    print(json.dumps(task_result, indent=2))
    # SHOULD RETURN RESULT HERE
    requests.post(CALLBACK_URL,
                  data=task_result,
                  headers={'X-Token': TOKEN}
                  )
