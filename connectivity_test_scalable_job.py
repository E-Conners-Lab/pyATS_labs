# connectivity_test_scalable_job.py
"""
Job file for Scalable Connectivity Test

Usage:
    pyats run job connectivity_test_scalable_job.py --testbed-file testbeds/testbed.yaml
"""

from pyats.easypy import run


def main(runtime):
    run(
        testscript='connectivity_test_scalable.py',
        runtime=runtime,
        taskid='Scalable_Connectivity_Test'
    )