# ospf_flap_test_advanced.py
"""
Advanced OSPF Interface Flap Test with Parameterization

Features:
- Test multiple devices and interfaces
- Customizable wait times
- Detailed logging and reporting
- JSON result export
"""

from pyats import aetest
from pyats.aetest import Testcase, test
import logging
import time
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)

# Test parameters - can be overridden from job file
parameters = {
    "test_configs": [
        {"device": "R1", "interface": "GigabitEthernet0/1"},
        {"device": "R1", "interface": "GigabitEthernet0/2"},
        # Add more test cases as needed
    ],
    "shutdown_wait": 3,  # Seconds to wait after shutdown
    "startup_wait": 5,  # Seconds to wait after no shutdown
    "convergence_timeout": 60,  # Max seconds to wait for OSPF convergence
    "convergence_check_interval": 5,  # Check interval in seconds
    "export_results": True,
    "results_dir": "results"
}


class CommonSetup(aetest.CommonSetup):
    """Common Setup Section"""

    @aetest.subsection
    def connect_to_devices(self, testbed):
        """Connect to all devices"""
        self.parent.parameters['connected_devices'] = {}

        for device in testbed.devices.values():
            try:
                device.connect(log_stdout=False)
                logger.info(f"✅ Connected to {device.name}")
                self.parent.parameters['connected_devices'][device.name] = device
            except Exception as e:
                logger.error(f"❌ Failed to connect to {device.name}: {e}")

    @aetest.subsection
    def verify_test_devices(self, testbed, test_configs):
        """Verify test devices are available and OSPF is running"""
        for config in test_configs:
            device_name = config['device']

            if device_name not in testbed.devices:
                self.failed(f"❌ Device {device_name} not found in testbed")

            device = testbed.devices[device_name]

            if not device.connected:
                self.failed(f"❌ Device {device_name} is not connected")

            # Verify OSPF is running
            try:
                output = device.execute("show ip ospf neighbor")
                if "Neighbor ID" not in output:
                    self.failed(f"❌ OSPF not running on {device_name}")
                logger.info(f"✅ OSPF verified on {device_name}")
            except Exception as e:
                self.failed(f"❌ Error verifying OSPF on {device_name}: {e}")

    @aetest.subsection
    def initialize_results_storage(self, results_dir):
        """Initialize results storage"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = os.path.join(results_dir, f"ospf_flap_{timestamp}")
        os.makedirs(output_dir, exist_ok=True)

        self.parent.parameters['output_dir'] = output_dir
        self.parent.parameters['test_results'] = []

        logger.info(f"📁 Results will be saved to: {output_dir}")


class TestOspfInterfaceFlap(Testcase):
    """Parameterized test for OSPF interface flapping"""

    @aetest.setup
    def setup(self):
        """Test setup"""
        self.test_results = []

    @test
    def flap_and_verify_ospf(self, testbed, test_configs, shutdown_wait,
                             startup_wait, convergence_timeout,
                             convergence_check_interval):
        """
        Flap interface and verify OSPF recovery

        This test loops through all test_configs
        """
        # Loop through each test configuration
        for test_config in test_configs:
            device_name = test_config['device']
            interface = test_config['interface']

            device = testbed.devices[device_name]

            test_result = {
                'device': device_name,
                'interface': interface,
                'start_time': datetime.now().isoformat(),
                'status': 'FAILED'
            }

            try:
                # Step 1: Capture baseline
                logger.info(f"{'=' * 80}")
                logger.info(f"🧪 Testing {device_name} - {interface}")
                logger.info(f"{'=' * 80}")

                baseline_output = device.execute("show ip ospf neighbor")
                baseline_neighbors = self._parse_neighbors(baseline_output)
                test_result['baseline_neighbors'] = baseline_neighbors

                logger.info(f"📊 Baseline: {len(baseline_neighbors)} OSPF neighbors")
                for neighbor_id, info in baseline_neighbors.items():
                    logger.info(f"   {neighbor_id}: {info['state']}")

                # Step 2: Shutdown interface
                logger.info(f"🔌 Shutting down {interface}...")
                device.configure([
                    f"interface {interface}",
                    "shutdown"
                ])
                time.sleep(shutdown_wait)

                # Verify interface is down
                intf_output = device.execute(f"show ip interface brief | include {interface}")
                if "down" not in intf_output.lower():
                    raise Exception(f"Interface {interface} did not go down")
                logger.info(f"✅ {interface} is DOWN")

                # Check OSPF neighbor loss
                after_shutdown = device.execute("show ip ospf neighbor")
                neighbors_down = self._parse_neighbors(after_shutdown)
                logger.info(f"📊 After shutdown: {len(neighbors_down)} OSPF neighbors")

                # Step 3: Bring interface back up
                logger.info(f"🔌 Bringing up {interface}...")
                device.configure([
                    f"interface {interface}",
                    "no shutdown"
                ])
                time.sleep(startup_wait)

                # Verify interface is up
                intf_output = device.execute(f"show ip interface brief | include {interface}")
                if "up" not in intf_output.lower():
                    raise Exception(f"Interface {interface} did not come back up")
                logger.info(f"✅ {interface} is UP")

                # Step 4: Wait for OSPF convergence
                convergence_start = time.time()
                converged = False

                logger.info("⏳ Waiting for OSPF convergence...")

                while (time.time() - convergence_start) < convergence_timeout:
                    current_output = device.execute("show ip ospf neighbor")
                    current_neighbors = self._parse_neighbors(current_output)

                    # Check if we have the same number of neighbors, all in FULL state
                    if len(current_neighbors) == len(baseline_neighbors):
                        all_full = all(
                            info['state'].startswith('FULL')
                            for info in current_neighbors.values()
                        )

                        if all_full:
                            elapsed = time.time() - convergence_start
                            logger.info(f"✅ OSPF converged in {elapsed:.1f} seconds")
                            test_result['convergence_time'] = elapsed
                            test_result['final_neighbors'] = current_neighbors
                            converged = True
                            break

                    elapsed = time.time() - convergence_start
                    logger.info(
                        f"   Still converging... ({elapsed:.1f}s) - {len(current_neighbors)}/{len(baseline_neighbors)} neighbors")
                    time.sleep(convergence_check_interval)

                if not converged:
                    raise Exception(f"OSPF did not converge within {convergence_timeout} seconds")

                # Step 5: Verify state matches baseline
                if current_neighbors == baseline_neighbors:
                    logger.info("✅ OSPF state fully restored to baseline")
                    test_result['status'] = 'PASSED'
                else:
                    logger.warning("⚠️  OSPF state differs from baseline")
                    test_result['status'] = 'PARTIAL'

            except Exception as e:
                logger.error(f"❌ Test failed: {e}")
                test_result['error'] = str(e)
                # Don't call self.failed() - continue with other tests

            finally:
                test_result['end_time'] = datetime.now().isoformat()
                self.test_results.append(test_result)
                logger.info(f"{'=' * 80}\n")

    @aetest.cleanup
    def save_results(self, export_results, output_dir):
        """Save test results to JSON"""
        if export_results and self.test_results:
            result_file = os.path.join(output_dir, "ospf_flap_results.json")

            with open(result_file, 'w') as f:
                json.dump(self.test_results, f, indent=2)

            logger.info(f"📊 Test results saved to: {result_file}")

            # Print summary
            logger.info("\n" + "=" * 80)
            logger.info("📊 TEST SUMMARY")
            logger.info("=" * 80)

            passed = sum(1 for r in self.test_results if r['status'] == 'PASSED')
            failed = sum(1 for r in self.test_results if r['status'] == 'FAILED')
            partial = sum(1 for r in self.test_results if r['status'] == 'PARTIAL')

            logger.info(f"✅ Passed:  {passed}")
            logger.info(f"⚠️  Partial: {partial}")
            logger.info(f"❌ Failed:  {failed}")
            logger.info(f"📋 Total:   {len(self.test_results)}")
            logger.info("=" * 80 + "\n")

    def _parse_neighbors(self, output):
        """Parse OSPF neighbor output"""
        neighbors = {}
        lines = output.split('\n')

        for line in lines:
            if line.strip() and not line.startswith('Neighbor'):
                parts = line.split()
                if len(parts) >= 5:
                    neighbor_id = parts[0]
                    state = parts[2]
                    interface = parts[5] if len(parts) > 5 else 'unknown'

                    neighbors[neighbor_id] = {
                        'state': state,
                        'interface': interface
                    }

        return neighbors


class CommonCleanup(aetest.CommonCleanup):
    """Common Cleanup Section"""

    @aetest.subsection
    def disconnect_devices(self, testbed):
        """Disconnect from all devices"""
        for device_name, device in testbed.devices.items():
            if device.connected:
                logger.info(f"🔌 Disconnecting from {device_name}")
                device.disconnect()

    @aetest.subsection
    def final_summary(self):
        """Print final summary"""
        logger.info("=" * 80)
        logger.info("🧪 OSPF Interface Flap Test Suite Completed")
        logger.info("=" * 80)


if __name__ == "__main__":
    import sys
    from pyats import aetest

    aetest.main()