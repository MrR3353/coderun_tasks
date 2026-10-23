import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
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
    """Caps RLIMIT_AS of the current process only. Used as a fallback when cgroup v2
    isn't available: a solution that spawns its own subprocesses could still exceed
    the intended total since each process gets its own separate cap.
    """
    limit_bytes = memory_limit_mb * 1024 * 1024

    def limiter():
        resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))

    return limiter


def _find_cgroup_root():
    """Finds the deepest ancestor cgroup (v2) that delegates the "memory" controller
    to its children, so a scoped cgroup can be created there to cap and measure a
    whole process tree's memory (not just one process, unlike RLIMIT_AS). Returns
    None if cgroup v2 / delegation isn't available (e.g. non-Linux, cgroup v1).
    """
    try:
        own_cgroup = Path("/proc/self/cgroup").read_text().strip()
    except OSError:
        return None
    if not own_cgroup.startswith("0::"):
        return None
    parts = own_cgroup[len("0::") :].strip("/").split("/")

    cgroup_fs = Path("/sys/fs/cgroup")
    best = None
    candidate = cgroup_fs
    for part in [None, *parts]:
        if part:
            candidate = candidate / part
        try:
            controllers = (candidate / "cgroup.subtree_control").read_text().split()
        except OSError:
            continue
        if "memory" in controllers:
            best = candidate
    return best


CGROUP_ROOT = _find_cgroup_root()


class _Cgroup:
    """A scoped cgroup v2 group for one test run: caps and measures the memory of the
    whole process tree launched under it (parent + any subprocesses it spawns), and
    can kill that whole tree atomically via cgroup.kill.
    """

    def __init__(self, path):
        self.path = path

    def join(self):
        """Moves the calling process into this cgroup. Pass as a subprocess preexec_fn
        so it runs in the child right after fork, before exec; any processes it later
        spawns inherit cgroup membership automatically.
        """
        (self.path / "cgroup.procs").write_text(str(os.getpid()))

    def kill(self):
        (self.path / "cgroup.kill").write_text("1")

    def peak_bytes(self):
        return int((self.path / "memory.peak").read_text())

    def close(self):
        self.path.rmdir()


def _make_cgroup(memory_limit_mb):
    """Creates a fresh scoped cgroup with the given memory cap. Returns None if cgroup
    v2 delegation isn't available or creating it fails for any reason, so callers can
    fall back to _limit_memory.
    """
    if CGROUP_ROOT is None:
        return None
    path = CGROUP_ROOT / f"coderun-tests-{os.getpid()}-{uuid.uuid4().hex[:8]}"
    try:
        path.mkdir()
        (path / "memory.max").write_text(str(memory_limit_mb * 1024 * 1024))
        (path / "memory.swap.max").write_text("0")
    except OSError:
        return None
    return _Cgroup(path)


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


def _run_posix(cmd, stdin, time_limit_s, preexec_fn, cgroup):
    """Runs cmd, polling with os.wait4 so we get this process's own exit status
    precisely. If `cgroup` is given, it caps and measures the whole process tree
    (parent + any subprocesses) and is killed as a unit on timeout; otherwise only
    the directly spawned process is killed/measured (resource.getrusage(RUSAGE_CHILDREN)
    would report a running max across all children, not just this one, so wait4's own
    rusage is used instead). Returns (returncode_or_None, stdout, stderr, elapsed_s, memory_kb).
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
                if cgroup is not None:
                    cgroup.kill()
                else:
                    proc.kill()
                os.wait4(proc.pid, 0)
                elapsed = time.perf_counter() - start
                return None, None, None, elapsed, None
            time.sleep(0.005)
        elapsed = time.perf_counter() - start
        returncode = os.waitstatus_to_exitcode(status)
        stdout_f.seek(0)
        stderr_f.seek(0)
        memory_kb = cgroup.peak_bytes() // 1024 if cgroup is not None else rusage.ru_maxrss
        return returncode, stdout_f.read(), stderr_f.read(), elapsed, memory_kb


def _run_fallback(cmd, stdin, time_limit_s, preexec_fn, cgroup):
    """Non-POSIX fallback: no peak-memory measurement, only timing. `cgroup` is unused
    here since cgroup v2 requires Linux.
    """
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
    memory_limit_mb = config.get("memory_limit_mb")
    cgroup = _make_cgroup(memory_limit_mb) if memory_limit_mb else None
    if cgroup is not None:
        preexec_fn = cgroup.join
    elif resource and memory_limit_mb:
        preexec_fn = _limit_memory(memory_limit_mb)
    else:
        preexec_fn = None
    expected = out_path.read_text()
    cmd = [sys.executable, str(script)]
    runner = _run_posix if os.name == "posix" else _run_fallback
    try:
        with in_path.open() as stdin:
            returncode, stdout, stderr, elapsed, memory_kb = runner(
                cmd, stdin, config["time_limit_s"], preexec_fn, cgroup
            )
    finally:
        if cgroup is not None:
            cgroup.close()

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
