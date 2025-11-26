from pyats.aetest import Testcase, test, main
from genie.testbed import load
import json
import os
from datetime import datetime

class ExportOspfData(Testcase):
    @test
    def gather_ospf_details(self, testbed):
        # Create output directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"results/ospf_export_{timestamp}"
        os.makedirs(output_dir, exist_ok=True)

        ospf_data = {}

        for device in testbed.devices.values():
            device.connect(log_stdout=False)
            print(f"Connected to {device.name}")

            ospf_data[device.name] = {
                "ospf_neighbor": device.execute("show ip ospf neighbor"),
                "ospf_int_brief": device.execute("show ip ospf interface brief"),
                "ip_int_brief": device.execute("show ip interface brief")
            }

        # Save to JSON
        output_file = os.path.join(output_dir, "ospf_detailed_export.json")
        with open(output_file, "w") as f:
            json.dump(ospf_data, f, indent=2)

        print(f"✅ OSPF data saved to {output_file}")

# Required for easypy
if __name__ == "__main__":
    main()
