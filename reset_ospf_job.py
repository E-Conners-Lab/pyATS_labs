# reset_ospf_job.py
from pyats.easypy import run

def main(runtime):
    run(
        testscript='reset_ospf_config.py',
        runtime=runtime,
        taskid='Reset_OSPF_Config'
    )