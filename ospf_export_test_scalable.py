# ospf_export_test_scalable.py
"""
Scalable OSPF Data Export with Parallel Connections

Features:
- Parallel device connections (scales to 50+ devices)
- Parallel data collection from all devices
- Exports complete OSPF data to JSON
- Generates summary and parsed exports

Usage:
    pyats run job ospf_export_detailed_json_scalable_job.py.py --testbed-file testbeds/testbed.yaml
"""

from pyats import aetest
import logging
import json
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


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
        logger.info("OSPF DATA EXPORT - SCALABLE VERSION")
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
        """Create directory for export results"""

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_dir = f"results/ospf_export_{timestamp}"
        os.makedirs(results_dir, exist_ok=True)

        self.parent.parameters['results_dir'] = results_dir

        logger.info(f"📁 Results will be saved to: {results_dir}")


class ExportOSPFData(aetest.Testcase):
    """Export OSPF Data from All Devices"""

    @aetest.test
    def gather_ospf_details(self, testbed, results_dir, max_workers=10):
        """
        Gather OSPF details from all devices IN PARALLEL

        Collects:
        - OSPF neighbors
        - OSPF interfaces
        - IP interfaces
        - OSPF routes
        - Loopback addresses
        """

        logger.info("=" * 80)
        logger.info("GATHERING OSPF DATA FROM ALL DEVICES (PARALLEL)")
        logger.info("=" * 80)

        all_data = {
            'export_timestamp': datetime.now().isoformat(),
            'device_count': len(testbed.devices),
            'devices': {}
        }

        def collect_from_device(device):
            """Collect all OSPF data from a single device - runs in thread"""
            import re
            device_name = device.name

            device_data = {
                'name': device_name,
                'management_ip': str(device.connections.main.ip) if hasattr(device.connections, 'main') else 'unknown',
                'ospf_neighbors': {},
                'ospf_interfaces': {},
                'ip_interfaces': {},
                'ospf_routes': [],
                'loopback': 'unknown'
            }

            errors = []

            # Collect OSPF Neighbors
            try:
                neighbors = device.parse("show ip ospf neighbor")
                device_data['ospf_neighbors'] = neighbors
            except Exception as e:
                errors.append(f"ospf_neighbors: {str(e)}")

            # Collect OSPF Interfaces
            try:
                ospf_intf = device.parse("show ip ospf interface brief")
                device_data['ospf_interfaces'] = ospf_intf
            except Exception as e:
                errors.append(f"ospf_interfaces: {str(e)}")

            # Collect IP Interfaces
            try:
                ip_intf = device.parse("show ip interface brief")
                device_data['ip_interfaces'] = ip_intf
            except Exception as e:
                errors.append(f"ip_interfaces: {str(e)}")

            # Collect OSPF Routes
            try:
                routes = device.parse("show ip route ospf")
                device_data['ospf_routes'] = routes
            except Exception as e:
                errors.append(f"ospf_routes: {str(e)}")

            # Get loopback address
            try:
                loopback = device.execute("show ip interface Loopback0 | include Internet address")
                match = re.search(r'Internet address is (\d+\.\d+\.\d+\.\d+)', loopback)
                if match:
                    device_data['loopback'] = match.group(1)
            except Exception:
                pass

            return (device_name, device_data, errors)

        # Parallel data collection
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_device = {
                executor.submit(collect_from_device, device): device
                for device in testbed.devices.values()
            }

            for future in as_completed(future_to_device):
                device_name, device_data, errors = future.result()
                all_data['devices'][device_name] = device_data

                # Count what we got
                neighbor_count = 0
                interfaces = device_data.get('ospf_neighbors', {}).get('interfaces', {})
                for intf, intf_data in interfaces.items():
                    neighbor_count += len(intf_data.get('neighbors', {}))

                if errors:
                    logger.warning(f"⚠️  {device_name}: Collected with {len(errors)} warnings")
                    for err in errors:
                        logger.warning(f"      {err}")
                else:
                    logger.info(
                        f"✅ {device_name}: {neighbor_count} neighbors, loopback: {device_data.get('loopback', 'unknown')}")

        # Store for later use
        self.parent.parameters['all_data'] = all_data

        logger.info("-" * 80)
        logger.info(f"Data collected from {len(all_data['devices'])} devices")

        self.passed(f"Collected data from {len(all_data['devices'])} devices")

    @aetest.test
    def generate_topology_data(self, results_dir):
        """Generate topology data for visualizations"""

        logger.info("=" * 80)
        logger.info("GENERATING TOPOLOGY DATA")
        logger.info("=" * 80)

        all_data = self.parent.parameters.get('all_data', {})

        topology = {
            'nodes': [],
            'links': []
        }

        # Create nodes
        for device_name, device_data in all_data.get('devices', {}).items():
            node = {
                'id': device_name,
                'label': device_name,
                'loopback': device_data.get('loopback', 'unknown'),
                'management_ip': device_data.get('management_ip', 'unknown')
            }
            topology['nodes'].append(node)
            logger.info(f"   📍 Node: {device_name}")

        # Create links from OSPF neighbor data
        links_seen = set()

        for device_name, device_data in all_data.get('devices', {}).items():
            neighbors = device_data.get('ospf_neighbors', {})
            interfaces = neighbors.get('interfaces', {})

            for intf_name, intf_data in interfaces.items():
                for neighbor_id, neighbor_info in intf_data.get('neighbors', {}).items():
                    # Create a unique link identifier (sorted to avoid duplicates)
                    link_key = tuple(sorted([device_name, neighbor_id]))

                    if link_key not in links_seen:
                        links_seen.add(link_key)

                        link = {
                            'source': device_name,
                            'target': neighbor_id,
                            'interface': intf_name,
                            'neighbor_address': neighbor_info.get('address', 'unknown'),
                            'state': neighbor_info.get('state', 'unknown')
                        }
                        topology['links'].append(link)
                        logger.info(f"   🔗 Link: {device_name} <-> {neighbor_id}")

        # Save topology
        topology_file = os.path.join(results_dir, 'network_topology.json')
        with open(topology_file, 'w') as f:
            json.dump(topology, f, indent=2)

        logger.info(f"\n📊 Topology: {len(topology['nodes'])} nodes, {len(topology['links'])} links")
        logger.info(f"📄 Saved to: {topology_file}")

        self.passed("Topology data generated")

    @aetest.test
    def save_complete_export(self, results_dir):
        """Save complete export data"""

        logger.info("=" * 80)
        logger.info("SAVING COMPLETE EXPORT")
        logger.info("=" * 80)

        all_data = self.parent.parameters.get('all_data', {})

        # Save complete data
        export_file = os.path.join(results_dir, 'ospf_complete_export.json')
        with open(export_file, 'w') as f:
            json.dump(all_data, f, indent=2)

        logger.info(f"📄 Complete export saved to: {export_file}")

        # Generate summary
        summary = {
            'timestamp': all_data.get('export_timestamp'),
            'device_count': all_data.get('device_count'),
            'devices': {}
        }

        for device_name, device_data in all_data.get('devices', {}).items():
            # Count neighbors
            neighbor_count = 0
            interfaces = device_data.get('ospf_neighbors', {}).get('interfaces', {})
            for intf, intf_data in interfaces.items():
                neighbor_count += len(intf_data.get('neighbors', {}))

            summary['devices'][device_name] = {
                'loopback': device_data.get('loopback', 'unknown'),
                'management_ip': device_data.get('management_ip', 'unknown'),
                'ospf_neighbors': neighbor_count
            }

        # Save summary
        summary_file = os.path.join(results_dir, 'export_summary.json')
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)

        logger.info(f"📄 Summary saved to: {summary_file}")

        # Print summary
        logger.info("\n" + "=" * 80)
        logger.info("EXPORT SUMMARY")
        logger.info("=" * 80)

        for device_name, info in summary['devices'].items():
            logger.info(f"  {device_name}:")
            logger.info(f"    Loopback: {info['loopback']}")
            logger.info(f"    Management: {info['management_ip']}")
            logger.info(f"    OSPF Neighbors: {info['ospf_neighbors']}")

        self.passed("Export completed successfully")


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