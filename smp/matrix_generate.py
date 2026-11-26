"""Drive Kit's real rename prompt with a deterministic single-candidate selection."""
import errno
import os
import pty
import select
import subprocess
import time


def rename_command(command, cwd, env):
    master, slave = pty.openpty()
    process = subprocess.Popen(command, cwd=cwd, env=env, stdin=slave, stdout=slave, stderr=slave)
    os.close(slave)
    output = bytearray()
    answered = False
    deadline = time.monotonic() + 120
    try:
        while True:
            if time.monotonic() > deadline:
                raise TimeoutError("Kit rename prompt timed out")
            ready, _, _ = select.select([master], [], [], 0.1)
            if ready:
                try:
                    chunk = os.read(master, 65536)
                except OSError as exc:
                    if exc.errno == errno.EIO:
                        break
                    raise
                if not chunk:
                    break
                output.extend(chunk)
                if not answered and b"renamed from" in output:
                    # There is exactly one dropped candidate in these fixtures.
                    os.write(master, b"\x1b[B")
                    time.sleep(0.05)
                    os.write(master, b"\r")
                    answered = True
            elif process.poll() is not None:
                break
        process.wait(timeout=5)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        os.close(master)
    return subprocess.CompletedProcess(command, process.returncode, output.decode(errors="replace"), "")
