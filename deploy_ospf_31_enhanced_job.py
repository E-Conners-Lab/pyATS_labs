# deploy_ospf_31_enhanced_job.py
"""
PyATS Job File for Enhanced OSPF /31 Deployment

This version includes point-to-point configuration to eliminate DR/BDR
elections and ensure 100% PASSED flap test results.

Usage:
    pyats run job deploy_ospf_31_enhanced_job.py --testbed-file testbeds/testbed.yaml
"""

from pyats.easypy import run


def main(runtime):
    """
    Main job entry point
    
    Args:
        runtime: PyATS runtime object containing testbed
    """
    
    # Run the enhanced OSPF deployment test script
    run(
        testscript='deploy_ospf_31_enhanced.py',
        runtime=runtime,
        taskid='Deploy_OSPF_31_Enhanced'
    )
