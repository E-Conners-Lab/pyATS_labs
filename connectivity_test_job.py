from pyats.easypy import Task

def main(runtime):
    testscript = 'connectivity_test.py'
    testbed = runtime.testbed

    Task(testscript=testscript, testbed=testbed).run()
