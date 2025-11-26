# connectivity_test_scalable.py
"""
Scalable Connectivity Test with Parallel Connections

This version connects to devices in parallel, making it suitable for
large testbeds (50+ devices).

Usage:
    pyats run job connectivity_test_scalable_job.py --testbed-file testbeds/testbed.yaml
"""

from pyats import aetest
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed  # <-- ADD THIS IMPORT

logger = logging.getLogger(__name__)


class CommonSetup(aetest.CommonSetup):
    """Common Setup Section"""

    @aetest.subsection
    def connect_to_devices(self, testbed, max_workers=10):
        """
        Connect to all devices in PARALLEL

        Args:
            testbed: pyATS testbed object
            max_workers: Max simultaneous connections (default 10)
                        - For 50 devices, use 10-15
                        - For 100+ devices, use 15-20
                        - Don't go too high or you'll overwhelm your machine
        """

        if testbed is None:
            self.failed("No testbed provided!")

        logger.info("=" * 80)
        logger.info(f"Connecting to {len(testbed.devices)} devices in parallel...")
        logger.info(f"Max concurrent connections: {max_workers}")
        logger.info("=" * 80)

        # Store testbed for later
        self.parent.parameters['testbed'] = testbed

        # Track results
        connected = []
        failed = []

        # =====================================================
        # THIS IS THE PARALLEL CONNECTION LOGIC
        # =====================================================
        def connect_one_device(device):
            """Connect to a single device - runs in thread"""
            try:
                device.connect(log_stdout=False)
                return (device.name, True, None)
            except Exception as e:
                return (device.name, False, str(e))

        # Use ThreadPoolExecutor for parallel connections
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all connection tasks
            future_to_device = {
                executor.submit(connect_one_device, device): device
                for device in testbed.devices.values()
            }

            # Process results as they complete
            for future in as_completed(future_to_device):
                device_name, success, error = future.result()

                if success:
                    logger.info(f"✅ Connected to {device_name}")
                    connected.append(device_name)
                else:
                    logger.error(f"❌ Failed to connect to {device_name}: {error}")
                    failed.append(device_name)
        # =====================================================
        # END OF PARALLEL LOGIC
        # =====================================================

        # Summary
        logger.info("=" * 80)
        logger.info(f"Connection Summary: {len(connected)}/{len(testbed.devices)} successful")
        logger.info("=" * 80)

        # Fail if any devices couldn't connect
        if failed:
            self.failed(f"Could not connect to: {', '.join(failed)}")


class ConnectivityTest(aetest.Testcase):
    """Test connectivity to all devices"""

    @aetest.test
    def check_interfaces(self, testbed):
        """Check GigabitEthernet0/0 on all devices"""

        logger.info("=" * 80)
        logger.info("Checking interfaces on all devices...")
        logger.info("=" * 80)

        results = []
        all_passed = True

        for device in testbed.devices.values():
            logger.info(f"\n🔍 Checking {device.name}...")

            try:
                parsed = device.parse("show ip interface brief")
                interfaces = parsed.get("interface", {})
                g0 = interfaces.get("GigabitEthernet0/0")

                if g0 and g0.get("ip_address") and g0.get("ip_address") != "unassigned":
                    ip = g0.get("ip_address")
                    logger.info(f"✅ {device.name} - Gi0/0 IP: {ip}")
                    results.append(f"{device.name} - GigabitEthernet0/0 IP is {ip}")
                else:
                    logger.error(f"❌ {device.name} - Gi0/0 has no IP")
                    results.append(f"{device.name} - GigabitEthernet0/0 has no IP")
                    all_passed = False

            except Exception as e:
                logger.error(f"❌ {device.name} - Error: {str(e)}")
                results.append(f"{device.name} - Error: {str(e)}")
                all_passed = False

        # Write report
        with open("interface_report.txt", "w") as f:
            f.write("Interface IP Check Report\n")
            f.write("=" * 40 + "\n\n")
            f.write("\n".join(results) + "\n")

        if all_passed:
            self.passed("All interfaces checked successfully")
        else:
            self.failed("One or more interface checks failed")


class CommonCleanup(aetest.CommonCleanup):
    """Common Cleanup Section"""

    @aetest.subsection
    def disconnect_from_devices(self, testbed, max_workers=10):
        """
        Disconnect from all devices in PARALLEL
        """

        if testbed is None:
            logger.warning("No testbed to disconnect from")
            return

        logger.info("=" * 80)
        logger.info("Disconnecting from all devices...")
        logger.info("=" * 80)

        def disconnect_one_device(device):
            """Disconnect from a single device"""
            try:
                if device.connected:
                    device.disconnect()
                return (device.name, True)
            except Exception as e:
                return (device.name, False)

        # Parallel disconnect
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(disconnect_one_device, device)
                for device in testbed.devices.values()
            ]

            for future in as_completed(futures):
                device_name, success = future.result()
                if success:
                    logger.info(f"✅ Disconnected from {device_name}")


if __name__ == "__main__":
    aetest.main()