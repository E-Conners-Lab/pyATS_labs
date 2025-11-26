# export_ospf_detailed_json.py

from pyats.easypy import Task

def main(runtime):
    # Run the AEtest script and pass the testbed
    Task(
        testscript='ospf_export_test.py',
        testbed=runtime.testbed
    ).run()
