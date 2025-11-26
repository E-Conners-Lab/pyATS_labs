# deploy_ospf_31_enhanced_scalable_job.py
from pyats.easypy import run

def main(runtime):
    run(
        testscript='deploy_ospf_31_enhanced_scalable.py',
        runtime=runtime,
        taskid='OSPF_31_P2P_Deployment'
    )
