# tests/genie_testscript.py

from pyats.aetest import Testcase, test, setup, cleanup, main
from genie.testbed import load
import re
import time

class VerifyOspfNeighborFlaps(Testcase):
    """Testcase to detect OSPF neighbor flaps"""

    @setup
    def setup_test(self, testbed):
        """Connect to all devices"""
        self.testbed = testbed
        self.testbed.connect(log_stdout=True)

    @test
    def check_ospf_neighbors(self):
        """Check OSPF neighbors for flapping events"""
        flap_detected = False

        for device in self.testbed.devices.values():
            try:
                output = device.parse('show ip ospf neighbor detail')
                for neighbor in output.get('interfaces', {}).values():
                    for n_data in neighbor.get('neighbors', {}).values():
                        if 'last_state_change' in n_data:
                            duration = n_data['last_state_change']
                            print(f"[{device.name}] Neighbor {n_data.get('neighbor_id')} last changed {duration} ago")
                            # You can implement stricter checks here
            except Exception as e:
                self.failed(f"{device.name}: Failed to check OSPF neighbors - {str(e)}")

        if flap_detected:
            self.failed("OSPF neighbor flap detected")
        else:
            self.passed("No OSPF neighbor flaps detected")

    @cleanup
    def disconnect(self):
        """Disconnect from all devices"""
        for device in self.testbed.devices.values():
            device.disconnect()


if __name__ == '__main__':
    import argparse
    from pyats.topology.loader import load

    parser = argparse.ArgumentParser()
    parser.add_argument('--testbed', type=str, required=True)
    args = parser.parse_args()

    testbed = load(args.testbed)
    main(testbed=testbed)
