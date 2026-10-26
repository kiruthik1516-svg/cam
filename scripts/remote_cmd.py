import subprocess
import sys

def run_remote(cmd):
    full_cmd = ["ssh", "-n", "-o", "ConnectTimeout=10", "-o", "StrictHostKeyChecking=no", "ubuntu@100.97.114.117", cmd]
    res = subprocess.run(full_cmd, capture_output=True, text=True)
    if res.stdout:
        print(res.stdout.strip())
    if res.stderr:
        print("STDERR:", res.stderr.strip())

if __name__ == '__main__':
    if len(sys.argv) > 1:
        run_remote(sys.argv[1])

