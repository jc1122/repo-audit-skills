import subprocess  # B404

PASSWORD = "hunter2"  # B105


def run(cmd):
    return subprocess.call(cmd, shell=True)  # B602
