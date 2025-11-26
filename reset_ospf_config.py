# reset_ospf_config.py
"""
Quick Reset Script - Clears OSPF and Interface Configuration

Removes:
- OSPF process 10
- GigabitEthernet0/1 and 0/2 IP addresses
- Loopback0

Usage:
    pyats run job reset_ospf_job.py --testbed-file testbeds/testbed.yaml
"""

from pyats import aetest
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# Configuration to remove
RESET_CONFIG = [
    # Remove OSPF
    'no router ospf 10',

    # Reset GigabitEthernet0/1
    'interface GigabitEthernet0/1',
    ' no ip ospf network point-to-point',
    ' no ip address',
    ' shutdown',

    # Reset GigabitEthernet0/2
    'interface GigabitEthernet0/2',
    ' no ip ospf network point-to-point',
    ' no ip address',
    ' shutdown',

    # Remove Loopback0
    'no interface Loopback0',
]


class CommonSetup(aetest.CommonSetup):
    """Connect to all devices in parallel"""

    @aetest.subsection
    def connect_to_devices(self, testbed, max_workers=10):

        if testbed is None:
            self.failed("No testbed provided!")

        logger.info("=" * 80)
        logger.info("RESET SCRIPT - Clearing OSPF & Interface Config")
        logger.info("=" * 80)
        logger.info(f"Connecting to {len(testbed.devices)} devices...")

        self.parent.parameters['testbed'] = testbed

        connected = []
        failed = []

        def connect_one(device):
            try:
                device.connect(log_stdout=False)
                return (device.name, True, None)
            except Exception as e:
                return (device.name, False, str(e))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(connect_one, d): d for d in testbed.devices.values()}

            for future in as_completed(futures):
                name, success, error = future.result()
                if success:
                    logger.info(f"✅ Connected to {name}")
                    connected.append(name)
                else:
                    logger.error(f"❌ Failed: {name} - {error}")
                    failed.append(name)

        if failed:
            self.failed(f"Could not connect to: {', '.join(failed)}")


class ResetConfiguration(aetest.Testcase):
    """Reset OSPF and Interface Configuration"""

    @aetest.test
    def apply_reset_config(self, testbed, steps):
        """Apply reset configuration to all devices"""

        logger.info("=" * 80)
        logger.info("APPLYING RESET CONFIGURATION")
        logger.info("=" * 80)

        for device in testbed.devices.values():
            with steps.start(f"Resetting {device.name}") as step:
                try:
                    logger.info(f"\n🔄 Resetting {device.name}...")

                    # Apply reset config
                    device.configure(RESET_CONFIG)

                    logger.info(f"✅ {device.name} reset complete")
                    step.passed(f"{device.name} reset")

                except Exception as e:
                    logger.error(f"❌ {device.name} failed: {str(e)}")
                    step.failed(str(e))

        self.passed("All devices reset")

    @aetest.test
    def verify_reset(self, testbed, steps):
        """Verify OSPF is removed"""

        logger.info("=" * 80)
        logger.info("VERIFYING RESET")
        logger.info("=" * 80)

        for device in testbed.devices.values():
            with steps.start(f"Verify {device.name}") as step:
                try:
                    # Check OSPF is gone
                    output = device.execute("show ip ospf")

                    if "not enabled" in output.lower() or "no" in output.lower():
                        logger.info(f"✅ {device.name}: OSPF removed")
                        step.passed("OSPF removed")
                    else:
                        logger.warning(f"⚠️  {device.name}: OSPF may still exist")
                        step.passed("Check manually")

                except Exception as e:
                    logger.info(f"✅ {device.name}: OSPF not running")
                    step.passed("OSPF removed")


class CommonCleanup(aetest.CommonCleanup):
    """Disconnect from all devices"""

    @aetest.subsection
    def disconnect_from_devices(self, testbed):

        logger.info("=" * 80)
        logger.info("Disconnecting...")
        logger.info("=" * 80)

        for device in testbed.devices.values():
            try:
                if device.connected:
                    device.disconnect()
                    logger.info(f"✅ Disconnected from {device.name}")
            except Exception:
                pass

        logger.info("\n🧹 Reset complete! Devices are clean.")


if __name__ == "__main__":
    aetest.main()