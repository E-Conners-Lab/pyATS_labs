# jobs/ospf_flap_job.py

from pyats.easypy import run

def main(runtime):
    run(
        testscript='tests/genie_testscript.py',
        testbed=runtime.testbed
    )
