# deploy_ospf_31_enhanced_scalable.py
"""
Scalable OSPF /31 Deployment with Point-to-Point Configuration

Features:
- Parallel device connections (scales to 50+ devices)
- Point-to-point OSPF network type (RFC 3021 best practice)
- No DR/BDR elections on /31 links
- Configurable max_workers for connection pooling

Usage:
    pyats run job deploy_ospf_31_enhanced_scalable_job.py --testbed-file testbeds/testbed.yaml
"""

from pyats import aetest
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# =====================================================
# OSPF CONFIGURATION DATA
# =====================================================
# For 50+ devices, you'd generate this from a YAML/CSV
# or pull from testbed.yaml custom attributes

OSPF_CONFIGS = {
    'R1': [
        'router ospf 10',
        ' router-id 1.1.1.1',
        ' network 1.1.1.1 0.0.0.0 area 10',
        ' network 10.0.0.0 0.0.0.3 area 10',
        'interface GigabitEthernet0/1',
        ' ip ospf network point-to-point',
        'interface GigabitEthernet0/2',
        ' ip ospf network point-to-point',
    ],
    'R2': [
        'router ospf 10',
        ' router-id 2.2.2.2',
        ' network 2.2.2.2 0.0.0.0 area 10',
        ' network 10.0.0.0 0.0.0.1 area 10',
        ' network 10.0.0.4 0.0.0.1 area 10',
        'interface GigabitEthernet0/1',
        ' ip ospf network point-to-point',
        'interface GigabitEthernet0/2',
        ' ip ospf network point-to-point',
    ],
    'R3': [
        'router ospf 10',
        ' router-id 3.3.3.3',
        ' network 3.3.3.3 0.0.0.0 area 10',
        ' network 10.0.0.4 0.0.0.3 area 10',
        'interface GigabitEthernet0/1',
        ' ip ospf network point-to-point',
        'interface GigabitEthernet0/2',
        ' ip ospf network point-to-point',
    ],
    'R4': [
        'router ospf 10',
        ' router-id 4.4.4.4',
        ' network 4.4.4.4 0.0.0.0 area 10',
        ' network 10.0.0.2 0.0.0.1 area 10',
        ' network 10.0.0.6 0.0.0.1 area 10',
        'interface GigabitEthernet0/1',
        ' ip ospf network point-to-point',
        'interface GigabitEthernet0/2',
        ' ip ospf network point-to-point',
    ],
}


class CommonSetup(aetest.CommonSetup):
    """Common Setup Section - Parallel Connections"""

    @aetest.subsection
    def connect_to_devices(self, testbed, max_workers=10):
        """
        Connect to all devices in PARALLEL

        Args:
            testbed: pyATS testbed object
            max_workers: Max simultaneous connections
                        - 4 devices: use 4
                        - 50 devices: use 10-15
                        - 100+ devices: use 15-20
        """

        if testbed is None:
            self.failed("No testbed provided!")

        logger.info("=" * 80)
        logger.info("OSPF /31 DEPLOYMENT WITH POINT-TO-POINT")
        logger.info("=" * 80)
        logger.info(f"Connecting to {len(testbed.devices)} devices in parallel...")
        logger.info(f"Max concurrent connections: {max_workers}")

        self.parent.parameters['testbed'] = testbed

        connected = []
        failed = []

        def connect_one_device(device):
            """Connect to a single device - runs in thread"""
            try:
                device.connect(log_stdout=False)
                return (device.name, True, None)
            except Exception as e:
                return (device.name, False, str(e))

        # Parallel connection execution
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_device = {
                executor.submit(connect_one_device, device): device
                for device in testbed.devices.values()
            }

            for future in as_completed(future_to_device):
                device_name, success, error = future.result()

                if success:
                    logger.info(f"✅ Connected to {device_name}")
                    connected.append(device_name)
                else:
                    logger.error(f"❌ Failed to connect to {device_name}: {error}")
                    failed.append(device_name)

        logger.info("-" * 80)
        logger.info(f"Connection Summary: {len(connected)}/{len(testbed.devices)} successful")

        if failed:
            self.failed(f"Could not connect to: {', '.join(failed)}")


class DeployOSPFConfig(aetest.Testcase):
    """Deploy OSPF Configuration with Point-to-Point"""

    @aetest.setup
    def setup(self, testbed):
        """Verify devices are ready for configuration"""
        logger.info("Verifying devices are ready for OSPF deployment...")

        for device in testbed.devices.values():
            if not device.connected:
                self.failed(f"{device.name} is not connected!")

    @aetest.test
    def deploy_ospf_config(self, testbed):
        """
        Deploy OSPF configuration to all devices

        Note: Config deployment is done sequentially for safety.
        Parallel config pushes can cause issues on some platforms.
        """

        logger.info("=" * 80)
        logger.info("DEPLOYING OSPF CONFIGURATION")
        logger.info("=" * 80)

        deployed = []
        failed = []

        for device in testbed.devices.values():
            device_name = device.name

            if device_name not in OSPF_CONFIGS:
                logger.warning(f"⚠️  No config defined for {device_name}, skipping...")
                continue

            logger.info(f"\n🔧 Configuring {device_name}...")

            try:
                config_lines = OSPF_CONFIGS[device_name]
                config_str = '\n'.join(config_lines)

                # Show what we're deploying
                logger.info(f"   Applying point-to-point OSPF config:")
                for line in config_lines:
                    if 'point-to-point' in line:
                        logger.info(f"   ➡️  {line.strip()}")

                # Apply configuration
                device.configure(config_str)

                logger.info(f"✅ {device_name} configured successfully")
                deployed.append(device_name)

            except Exception as e:
                logger.error(f"❌ Failed to configure {device_name}: {str(e)}")
                failed.append(device_name)

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("DEPLOYMENT SUMMARY")
        logger.info("=" * 80)
        logger.info(f"✅ Deployed: {len(deployed)} devices")
        logger.info(f"❌ Failed: {len(failed)} devices")

        if failed:
            self.failed(f"Failed to configure: {', '.join(failed)}")
        else:
            self.passed(f"Successfully deployed OSPF to {len(deployed)} devices")


class VerifyOSPFNeighbors(aetest.Testcase):
    """Verify OSPF Neighbors are UP"""

    @aetest.test
    def check_ospf_neighbors(self, testbed, steps, wait_time=30):
        """
        Verify OSPF neighbors are established

        Args:
            wait_time: Seconds to wait for OSPF convergence
        """

        import time

        logger.info("=" * 80)
        logger.info(f"VERIFYING OSPF NEIGHBORS (waiting {wait_time}s for convergence)")
        logger.info("=" * 80)

        # Wait for OSPF to converge
        logger.info(f"⏳ Waiting {wait_time} seconds for OSPF convergence...")
        time.sleep(wait_time)

        all_passed = True
        results = []

        for device in testbed.devices.values():
            with steps.start(f"Checking {device.name} OSPF neighbors") as step:
                try:
                    output = device.parse("show ip ospf neighbor")
                    interfaces = output.get("interfaces", {})

                    neighbor_count = 0
                    for intf, intf_data in interfaces.items():
                        neighbors = intf_data.get("neighbors", {})
                        neighbor_count += len(neighbors)

                        for neighbor_id, neighbor_data in neighbors.items():
                            state = neighbor_data.get("state", "UNKNOWN")
                            logger.info(f"   {device.name} → {neighbor_id}: {state} via {intf}")

                            # Check for FULL state (FULL/- for P2P)
                            if "FULL" in state:
                                results.append(f"✅ {device.name} → {neighbor_id}: {state}")
                            else:
                                results.append(f"⚠️  {device.name} → {neighbor_id}: {state}")
                                all_passed = False

                    if neighbor_count == 0:
                        logger.error(f"❌ {device.name} has no OSPF neighbors!")
                        results.append(f"❌ {device.name}: No neighbors found")
                        all_passed = False
                        step.failed(f"{device.name} has no OSPF neighbors")
                    else:
                        step.passed(f"{device.name} has {neighbor_count} neighbors")

                except Exception as e:
                    logger.error(f"❌ Error checking {device.name}: {str(e)}")
                    results.append(f"❌ {device.name}: Error - {str(e)}")
                    all_passed = False
                    step.failed(str(e))

        # Write verification report
        with open("ospf_deploy_report.txt", "w") as f:
            f.write("OSPF Deployment Verification Report\n")
            f.write("=" * 50 + "\n")
            f.write("Configuration: Point-to-Point (RFC 3021)\n")
            f.write("=" * 50 + "\n\n")
            f.write("\n".join(results) + "\n")

        logger.info("\n📄 Report saved to: ospf_deploy_report.txt")

        if all_passed:
            self.passed("All OSPF neighbors are FULL")
        else:
            self.failed("Some OSPF neighbors are not FULL")


class VerifyPointToPoint(aetest.Testcase):
    """Verify Point-to-Point Configuration"""

    @aetest.test
    def check_interface_type(self, testbed):
        """Verify interfaces are configured as point-to-point"""

        logger.info("=" * 80)
        logger.info("VERIFYING POINT-TO-POINT CONFIGURATION")
        logger.info("=" * 80)

        all_p2p = True

        for device in testbed.devices.values():
            logger.info(f"\n🔍 Checking {device.name}...")

            try:
                output = device.parse("show ip ospf interface brief")
                interfaces = output.get("instance", {}).get("10", {}).get("areas", {}).get("0.0.0.10", {}).get(
                    "interfaces", {})

                for intf_name, intf_data in interfaces.items():
                    intf_type = intf_data.get("interface_type", "UNKNOWN")
                    state = intf_data.get("state", "UNKNOWN")

                    if "Loopback" in intf_name:
                        continue  # Skip loopbacks

                    if "POINT" in intf_type.upper() or "P2P" in intf_type.upper():
                        logger.info(f"   ✅ {intf_name}: {intf_type} ({state})")
                    else:
                        logger.warning(f"   ⚠️  {intf_name}: {intf_type} (expected POINT_TO_POINT)")
                        all_p2p = False

            except Exception as e:
                logger.error(f"   ❌ Error: {str(e)}")
                all_p2p = False

        if all_p2p:
            self.passed("All interfaces are Point-to-Point")
        else:
            self.failed("Some interfaces are not Point-to-Point")


class CommonCleanup(aetest.CommonCleanup):
    """Common Cleanup Section - Parallel Disconnect"""

    @aetest.subsection
    def disconnect_from_devices(self, testbed, max_workers=10):
        """Disconnect from all devices in parallel"""

        if testbed is None:
            return

        logger.info("=" * 80)
        logger.info("Disconnecting from all devices...")
        logger.info("=" * 80)

        def disconnect_one(device):
            try:
                if device.connected:
                    device.disconnect()
                return (device.name, True)
            except Exception:
                return (device.name, False)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(disconnect_one, d)
                for d in testbed.devices.values()
            ]

            for future in as_completed(futures):
                name, success = future.result()
                if success:
                    logger.info(f"✅ Disconnected from {name}")


if __name__ == "__main__":
    aetest.main()