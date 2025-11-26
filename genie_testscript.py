# genie_testscript.py

from pyats.aetest import Testcase, test, main
from ospf_flap_trigger import TriggerFlapOspfInterface


class CommonSetup(Testcase):
    @test
    def connect(self, testbed):
        for device in testbed.devices.values():
            device.connect()


class TriggerTest(Testcase):
    @test
    def run_trigger(self, testbed):
        trigger = TriggerFlapOspfInterface()
        trigger.testbed = testbed
        trigger.verify_prerequisite()
        trigger.execute()


if __name__ == "__main__":
    import argparse
    from pyats.easypy import run

    parser = argparse.ArgumentParser()
    parser.add_argument('--testbed', required=True)
    args = parser.parse_args()

    run(testscript='genie_testscript.py', testbed=args.testbed)
