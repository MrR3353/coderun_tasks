import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

try:
    import resource
except ImportError:
    resource = None

ROOT = Path(__file__).resolve().parent
TASKS_DIR = ROOT / "tasks"

DEFAULT_CONFIG = {"time_limit_s": 5, "memory_limit_mb": 256}


def load_config(task_dir):
    """Reads tasks/<task_num>/tests/config.json, falling back to defaults for missing keys."""
    config = dict(DEFAULT_CONFIG)
    config_path = task_dir / "tests" / "config.json"
    if config_path.exists():
        config.update(json.loads(config_path.read_text()))
    return config


def _limit_memory(memory_limit_mb):
    limit_bytes = memory_limit_mb * 1024 * 1024

    def limiter():
        resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))

    return limiter


def discover_tests(tasks_dir=TASKS_DIR):
    """Returns {task_num: [(test_num, in_path, out_path), ...]} sorted by test_num."""
    tasks = {}
    if not tasks_dir.exists():
        return tasks
    for task_dir in tasks_dir.iterdir():
        if not task_dir.is_dir():
            continue
        tests_dir = task_dir / "tests"
        if not tests_dir.exists():
            continue
        tests = []
        for in_path in tests_dir.glob("*_in.txt"):
            test_num = in_path.name[: -len("_in.txt")]
            out_path = tests_dir / f"{test_num}_out.txt"
            if out_path.exists():
                tests.append((test_num, in_path, out_path))
        tests.sort(key=lambda t: int(t[0]))
        if tests:
            tasks[task_dir.name] = tests
    return tasks


def _run_posix(cmd, stdin, time_limit_s, preexec_fn):
    """Runs cmd, polling with os.wait4 so we get this process's own peak RSS
    (resource.getrusage(RUSAGE_CHILDREN) would report a running max across all
    children, not this one). Returns (returncode_or_None, stdout, stderr, elapsed_s, memory_kb).
    None returncode means the process was killed for exceeding time_limit_s.
    """
    with tempfile.TemporaryFile(mode="w+") as stdout_f, tempfile.TemporaryFile(mode="w+") as stderr_f:
        start = time.perf_counter()
        proc = subprocess.Popen(cmd, stdin=stdin, stdout=stdout_f, stderr=stderr_f, preexec_fn=preexec_fn)
        deadline = start + time_limit_s
        while True:
            reaped_pid, status, rusage = os.wait4(proc.pid, os.WNOHANG)
            if reaped_pid == proc.pid:
                break
            if time.perf_counter() > deadline:
                proc.kill()
                os.wait4(proc.pid, 0)
                elapsed = time.perf_counter() - start
                return None, None, None, elapsed, None
            time.sleep(0.005)
        elapsed = time.perf_counter() - start
        returncode = os.waitstatus_to_exitcode(status)
        stdout_f.seek(0)
        stderr_f.seek(0)
        return returncode, stdout_f.read(), stderr_f.read(), elapsed, rusage.ru_maxrss


def _run_fallback(cmd, stdin, time_limit_s, preexec_fn):
    """Non-POSIX fallback: no peak-memory measurement, only timing."""
    start = time.perf_counter()
    try:
        result = subprocess.run(
            cmd, stdin=stdin, capture_output=True, text=True, timeout=time_limit_s, preexec_fn=preexec_fn
        )
    except subprocess.TimeoutExpired:
        return None, None, None, time.perf_counter() - start, None
    elapsed = time.perf_counter() - start
    return result.returncode, result.stdout, result.stderr, elapsed, None


def run_test(task_num, in_path, out_path, tasks_dir=TASKS_DIR, config=None):
    """Runs tasks/<task_num>/solution.py with in_path as stdin, compares stdout to out_path.

    Applies the task's time/memory limits from tests/config.json (see load_config).
    Returns (passed, actual, expected, error, elapsed_s, memory_kb).
    """
    task_dir = tasks_dir / str(task_num)
    script = task_dir / "solution.py"
    if config is None:
        config = load_config(task_dir)
    preexec_fn = (
        _limit_memory(config["memory_limit_mb"])
        if resource and config.get("memory_limit_mb")
        else None
    )
    expected = out_path.read_text()
    cmd = [sys.executable, str(script)]
    runner = _run_posix if os.name == "posix" else _run_fallback
    with in_path.open() as stdin:
        returncode, stdout, stderr, elapsed, memory_kb = runner(cmd, stdin, config["time_limit_s"], preexec_fn)

    if returncode is None:
        return False, None, expected, f"timed out after {config['time_limit_s']}s", elapsed, memory_kb
    if returncode != 0:
        error = stderr.strip() or f"завершился с кодом {returncode}"
        return False, stdout, expected, error, elapsed, memory_kb

    passed = stdout.rstrip("\n") == expected.rstrip("\n")
    return passed, stdout, expected, None, elapsed, memory_kb


def run_task_tests(task_num, tasks_dir=TASKS_DIR):
    """Runs all tests for a single task. Returns True if all passed."""
    tests = discover_tests(tasks_dir).get(str(task_num), [])
    if not tests:
        print(f"Задача {task_num}: тесты не найдены")
        return False

    config = load_config(tasks_dir / str(task_num))
    all_passed = True
    for test_num, in_path, out_path in tests:
        passed, actual, expected, error, elapsed, memory_kb = run_test(
            task_num, in_path, out_path, tasks_dir, config
        )
        all_passed &= passed
        status = "OK" if passed else "FAIL"
        stats = f"{elapsed:.2f} с"
        if memory_kb is not None:
            stats += f", {memory_kb / 1024:.1f} МБ"
        print(f"Задача {task_num}, тест {test_num}: {status} ({stats})")
        if not passed:
            if error:
                print(f"  ошибка: {error}")
            else:
                print(f"  ожидалось: {expected.rstrip(chr(10))!r}")
                print(f"  получено:  {actual.rstrip(chr(10))!r}")
    return all_passed


def run_all(tasks_dir=TASKS_DIR):
    """Runs tests for every task found. Returns True if all passed."""
    tasks = discover_tests(tasks_dir)
    if not tasks:
        print("Тесты не найдены")
        return False
    all_passed = True
    for task_num in sorted(tasks, key=int):
        all_passed &= run_task_tests(task_num, tasks_dir)
    return all_passed


if __name__ == "__main__":
    task_numbers = sys.argv[1:]
    if task_numbers:
        ok = all(run_task_tests(n) for n in task_numbers)
    else:
        ok = run_all()
    sys.exit(0 if ok else 1)
