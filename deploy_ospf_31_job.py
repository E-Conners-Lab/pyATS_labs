from pyats.easypy import Task

def main(runtime):
    testscript = "deploy_ospf_31.py"
    testbed = runtime.testbed

    Task(testscript=testscript, testbed=testbed).run()

