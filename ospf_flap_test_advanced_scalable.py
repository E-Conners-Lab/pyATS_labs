# ospf_flap_test_advanced_scalable.py
"""
Scalable OSPF Interface Flap Test with Parallel Connections

Features:
- Parallel device connections (scales to 50+ devices)
- Tests OSPF resilience by flapping interfaces
- Measures convergence time
- Compares baseline to post-flap state
- Generates JSON results

Usage:
    pyats run job ospf_flap_job_advanced_scalable.py --testbed-file testbeds/testbed.yaml
"""

from pyats import aetest
import logging
import time
import json
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

# =====================================================
# TEST CONFIGURATION
# =====================================================
# Define which interfaces to test on which devices
# For 50+ devices, you'd generate this from testbed data or config file

TEST_CONFIGS = [
    {'device': 'R1', 'interface': 'GigabitEthernet0/1'},
    {'device': 'R1', 'interface': 'GigabitEthernet0/2'},
]

# Timing configuration
FLAP_DOWN_TIME = 5  # Seconds to keep interface down
CONVERGENCE_TIMEOUT = 30  # Max seconds to wait for OSPF reconvergence
POLL_INTERVAL = 0.5  # Seconds between convergence checks
SLA_TARGET = 10.0  # SLA target in seconds


class CommonSetup(aetest.CommonSetup):
    """Common Setup Section - Parallel Connections"""

    @aetest.subsection
    def connect_to_devices(self, testbed, max_workers=10):
        """
        Connect to all devices in PARALLEL

        Args:
            testbed: pyATS testbed object
            max_workers: Max simultaneous connections
        """

        if testbed is None:
            self.failed("No testbed provided!")

        logger.info("=" * 80)
        logger.info("OSPF INTERFACE FLAP TEST - SCALABLE VERSION")
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

    @aetest.subsection
    def create_results_directory(self):
        """Create directory for test results"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = f"results/ospf_flap_{timestamp}"
        os.makedirs(results_dir, exist_ok=True)

        self.parent.parameters['results_dir'] = results_dir
        self.parent.parameters['test_results'] = []

        logger.info(f"📁 Results will be saved to: {results_dir}")


class OSPFFlapTest(aetest.Testcase):
    """OSPF Interface Flap Test"""

    @aetest.setup
    def setup(self, testbed):
        """Verify test device exists"""
        for test_config in TEST_CONFIGS:
            device_name = test_config['device']
            if device_name not in testbed.devices:
                self.failed(f"Test device {device_name} not in testbed!")

    @aetest.test
    @aetest.loop(test_config=TEST_CONFIGS)
    def flap_interface_test(self, testbed, steps, test_config, results_dir):
        """
        Flap interface and measure OSPF convergence

        This test:
        1. Captures baseline OSPF neighbors
        2. Shuts down the interface
        3. Verifies neighbor goes down
        4. Brings interface back up
        5. Measures time to reconverge
        6. Compares final state to baseline
        """

        device_name = test_config['device']
        interface = test_config['interface']
        device = testbed.devices[device_name]

        logger.info("=" * 80)
        logger.info(f"TESTING: {device_name} - {interface}")
        logger.info("=" * 80)

        test_result = {
            'device': device_name,
            'interface': interface,
            'timestamp': datetime.now().isoformat(),
            'baseline_neighbors': 0,
            'final_neighbors': 0,
            'convergence_time': None,
            'status': 'UNKNOWN',
            'details': {}
        }

        # =====================================================
        # STEP 1: Capture Baseline
        # =====================================================
        with steps.start(f"Capture baseline OSPF state on {device_name}") as step:
            try:
                baseline = device.parse("show ip ospf neighbor")
                baseline_neighbors = self._count_full_neighbors(baseline)
                test_result['baseline_neighbors'] = baseline_neighbors
                test_result['details']['baseline'] = self._extract_neighbor_info(baseline)

                logger.info(f"📊 Baseline: {baseline_neighbors} neighbors in FULL state")

                if baseline_neighbors == 0:
                    step.failed("No OSPF neighbors found in baseline!")

            except Exception as e:
                step.failed(f"Failed to capture baseline: {str(e)}")

        # =====================================================
        # STEP 2: Shutdown Interface
        # =====================================================
        with steps.start(f"Shutdown {interface}") as step:
            try:
                device.configure([
                    f"interface {interface}",
                    "shutdown"
                ])
                logger.info(f"🔴 Interface {interface} shut down")

            except Exception as e:
                step.failed(f"Failed to shutdown interface: {str(e)}")

        # =====================================================
        # STEP 3: Wait and Verify Neighbor Down
        # =====================================================
        with steps.start("Verify neighbor goes down") as step:
            time.sleep(FLAP_DOWN_TIME)

            try:
                during_flap = device.parse("show ip ospf neighbor")
                during_count = self._count_full_neighbors(during_flap)

                logger.info(f"📉 During flap: {during_count} neighbors (was {baseline_neighbors})")

                if during_count >= baseline_neighbors:
                    logger.warning("⚠️  Neighbor count didn't decrease - interface may not have gone down")

            except Exception as e:
                logger.warning(f"Could not verify during flap: {str(e)}")

        # =====================================================
        # STEP 4: Bring Interface Up and Measure Convergence
        # =====================================================
        with steps.start(f"Bring {interface} back up and measure convergence") as step:
            try:
                # Bring interface up
                device.configure([
                    f"interface {interface}",
                    "no shutdown"
                ])
                logger.info(f"🟢 Interface {interface} brought back up")

                # Start convergence timer
                start_time = time.time()
                converged = False

                logger.info(f"⏱️  Waiting for convergence (timeout: {CONVERGENCE_TIMEOUT}s)...")

                while (time.time() - start_time) < CONVERGENCE_TIMEOUT:
                    try:
                        current = device.parse("show ip ospf neighbor")
                        current_count = self._count_full_neighbors(current)

                        if current_count >= baseline_neighbors:
                            convergence_time = time.time() - start_time
                            test_result['convergence_time'] = round(convergence_time, 2)
                            converged = True
                            logger.info(f"✅ Converged in {convergence_time:.2f} seconds!")
                            break

                    except Exception:
                        pass

                    time.sleep(POLL_INTERVAL)

                if not converged:
                    test_result['convergence_time'] = CONVERGENCE_TIMEOUT
                    step.failed(f"Did not converge within {CONVERGENCE_TIMEOUT} seconds")

            except Exception as e:
                step.failed(f"Failed during convergence test: {str(e)}")

        # =====================================================
        # STEP 5: Compare Final State to Baseline
        # =====================================================
        with steps.start("Compare final state to baseline") as step:
            try:
                final = device.parse("show ip ospf neighbor")
                final_neighbors = self._count_full_neighbors(final)
                test_result['final_neighbors'] = final_neighbors
                test_result['details']['final'] = self._extract_neighbor_info(final)

                # Compare
                baseline_info = test_result['details']['baseline']
                final_info = test_result['details']['final']

                if final_neighbors >= baseline_neighbors:
                    # Check if all neighbors match
                    all_match = True
                    for neighbor_id, baseline_data in baseline_info.items():
                        if neighbor_id in final_info:
                            # For P2P, we just check FULL state (no role comparison)
                            if 'FULL' in final_info[neighbor_id].get('state', ''):
                                continue
                        all_match = False
                        break

                    if all_match:
                        test_result['status'] = 'PASSED'
                        logger.info(f"✅ PASSED - All {final_neighbors} neighbors restored")
                    else:
                        test_result['status'] = 'PARTIAL'
                        logger.warning(f"⚠️  PARTIAL - Neighbors restored but state differs")
                else:
                    test_result['status'] = 'FAILED'
                    logger.error(f"❌ FAILED - Only {final_neighbors}/{baseline_neighbors} neighbors restored")

            except Exception as e:
                test_result['status'] = 'ERROR'
                step.failed(f"Failed to compare states: {str(e)}")

        # =====================================================
        # Store Result
        # =====================================================
        self.parent.parameters['test_results'].append(test_result)

        # Log summary
        logger.info("-" * 40)
        logger.info(f"TEST RESULT: {test_result['status']}")
        logger.info(f"Convergence: {test_result['convergence_time']}s (SLA: {SLA_TARGET}s)")
        logger.info("-" * 40)

        # Set test result
        if test_result['status'] == 'PASSED':
            self.passed(f"Interface {interface} flap test passed")
        elif test_result['status'] == 'PARTIAL':
            self.passx(f"Interface {interface} flap test partial - check details")
        else:
            self.failed(f"Interface {interface} flap test failed")

    def _count_full_neighbors(self, parsed_output):
        """Count neighbors in FULL state"""
        count = 0
        interfaces = parsed_output.get("interfaces", {})
        for intf, intf_data in interfaces.items():
            neighbors = intf_data.get("neighbors", {})
            for neighbor_id, neighbor_data in neighbors.items():
                state = neighbor_data.get("state", "")
                if "FULL" in state:
                    count += 1
        return count

    def _extract_neighbor_info(self, parsed_output):
        """Extract neighbor information for comparison"""
        info = {}
        interfaces = parsed_output.get("interfaces", {})
        for intf, intf_data in interfaces.items():
            neighbors = intf_data.get("neighbors", {})
            for neighbor_id, neighbor_data in neighbors.items():
                info[neighbor_id] = {
                    'interface': intf,
                    'state': neighbor_data.get("state", "UNKNOWN"),
                    'address': neighbor_data.get("address", "UNKNOWN")
                }
        return info


class GenerateReport(aetest.Testcase):
    """Generate Test Report"""

    @aetest.test
    def generate_json_report(self, results_dir):
        """Generate JSON report of all test results"""

        test_results = self.parent.parameters.get('test_results', [])

        if not test_results:
            self.skipped("No test results to report")
            return

        # Calculate summary
        passed = sum(1 for r in test_results if r['status'] == 'PASSED')
        partial = sum(1 for r in test_results if r['status'] == 'PARTIAL')
        failed = sum(1 for r in test_results if r['status'] not in ['PASSED', 'PARTIAL'])

        convergence_times = [r['convergence_time'] for r in test_results if r['convergence_time']]
        avg_convergence = sum(convergence_times) / len(convergence_times) if convergence_times else 0

        report = {
            'test_name': 'OSPF Interface Flap Test (Scalable)',
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': len(test_results),
                'passed': passed,
                'partial': partial,
                'failed': failed,
                'success_rate': f"{(passed + partial) / len(test_results) * 100:.1f}%",
                'average_convergence': f"{avg_convergence:.2f}s",
                'sla_target': f"{SLA_TARGET}s",
                'sla_met': avg_convergence <= SLA_TARGET
            },
            'results': test_results
        }

        # Write report
        report_file = os.path.join(results_dir, 'flap_test_results.json')
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info("=" * 80)
        logger.info("FINAL SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total Tests: {len(test_results)}")
        logger.info(f"Passed: {passed} | Partial: {partial} | Failed: {failed}")
        logger.info(f"Average Convergence: {avg_convergence:.2f}s (SLA: {SLA_TARGET}s)")
        logger.info(f"📄 Report saved to: {report_file}")

        self.passed("Report generated successfully")


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