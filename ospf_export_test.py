from pyats import aetest
from pyats.aetest import Testcase, test, main
import json
import os
from datetime import datetime
import logging

# Get the logger
logger = logging.getLogger(__name__)


class ExportOspfData(Testcase):

    @test
    def gather_ospf_details(self):
        testbed = self.parent.parameters['testbed']

        # Create timestamped results directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join("results", f"ospf_export_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)  # ✅ This line creates the directory

        ospf_data = {}

        for device in testbed.devices.values():
            try:
                device.connect(log_stdout=False)
                logger.info(f"✅ Connected to {device.name}")

                ospf_data[device.name] = {
                    "ospf_neighbor": device.execute("show ip ospf neighbor"),
                    "ospf_interface_brief": device.execute("show ip ospf interface brief"),
                    "ip_interface_brief": device.execute("show ip interface brief")
                }

                device.disconnect()

            except Exception as e:
                ospf_data[device.name] = {"error": str(e)}
                logger.error(f"❌ Error on {device.name}: {e}")

        output_file = os.path.join(output_dir, "ospf_detailed_export.json")
        with open(output_file, "w") as f:
            json.dump(ospf_data, f, indent=2)

        logger.info(f"📦 Exported OSPF data to: {output_file}")


class CommonCleanup(aetest.CommonCleanup):
    """Cleanup Section"""

    @aetest.subsection
    def disconnect_devices(self, testbed):
        """Disconnect from all devices"""
        for device_name, device in testbed.devices.items():
            if device.connected:
                logger.info(f"🔌 Disconnecting from {device_name}")  # ✅ Changed to logger.info
                device.disconnect()
                logger.info(f"✅ Successfully disconnected from {device_name}")  # ✅ Changed
            else:
                logger.info(f"ℹ️  {device_name} was not connected")  # ✅ Changed

    @aetest.subsection
    def cleanup_summary(self):
        """Print cleanup summary"""
        logger.info("=" * 80)  # ✅ Changed to logger.info
        logger.info("🧹 Cleanup completed successfully")  # ✅ Changed
        logger.info("=" * 80)  # ✅ Changed


if __name__ == "__main__":
    main()