import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TASKS_DIR = ROOT / "tasks"


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


def run_test(task_num, in_path, out_path, tasks_dir=TASKS_DIR, timeout=10):
    """Runs tasks/<task_num>/solution.py with in_path as stdin, compares stdout to out_path.

    Returns (passed, actual, expected, error).
    """
    script = tasks_dir / str(task_num) / "solution.py"
    expected = out_path.read_text()
    with in_path.open() as stdin:
        try:
            result = subprocess.run(
                [sys.executable, str(script)],
                stdin=stdin,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return False, None, expected, f"timed out after {timeout}s"

    if result.returncode != 0:
        return False, result.stdout, expected, result.stderr.strip()

    actual = result.stdout
    passed = actual.rstrip("\n") == expected.rstrip("\n")
    return passed, actual, expected, None


def run_task_tests(task_num, tasks_dir=TASKS_DIR):
    """Runs all tests for a single task. Returns True if all passed."""
    tests = discover_tests(tasks_dir).get(str(task_num), [])
    if not tests:
        print(f"Задача {task_num}: тесты не найдены")
        return False

    all_passed = True
    for test_num, in_path, out_path in tests:
        passed, actual, expected, error = run_test(task_num, in_path, out_path, tasks_dir)
        all_passed &= passed
        status = "OK" if passed else "FAIL"
        print(f"Задача {task_num}, тест {test_num}: {status}")
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
