# ospf_flap_job_advanced_scalable.py
from pyats.easypy import run

def main(runtime):
    run(
        testscript='ospf_flap_test_advanced_scalable.py',
        runtime=runtime,
        taskid='OSPF_Flap_Test_Scalable'
    )
