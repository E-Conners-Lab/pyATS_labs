from pyats import aetest
from ipaddress import ip_network
import logging

log = logging.getLogger(__name__)

# Topology Description

# Each link is two endpoints: (device_name, interface_name)
LINKS = [
    {
        "name": "R1_R2_G0_1",
        "endpoints": [
            ("R1", "GigabitEthernet0/1"),
            ("R2", "GigabitEthernet0/1"),
        ],
    },
    {
        "name": "R1_R4_G0_2",
        "endpoints": [
            ("R1", "GigabitEthernet0/2"),
            ("R4", "GigabitEthernet0/2"),
        ],
    },
    {
        "name": "R2_R3_G0_2",
        "endpoints": [
            ("R2", "GigabitEthernet0/2"),
            ("R3", "GigabitEthernet0/2"),
        ],
    },
    {
        "name": "R3_R4_G0_1",
        "endpoints": [
            ("R3", "GigabitEthernet0/1"),
            ("R4", "GigabitEthernet0/1"),
        ],
    },
]

# Base pool to carve /31s
LINK_POOL = ip_network("10.0.0.0/24")
OSPF_PROCESS_ID = 10
OSPF_AREA = 10


# -----  Common Setup  --------

class CommonSetup(aetest.CommonSetup):
    """ Common Setup """

    @aetest.subsection
    def connect_to_testbed(self, testbed):
        """Connect to all devices defined in the testbed."""
        log.info("+" * 78)
        log.info("|            Loading testbed and connecting to all devices...       |")
        log.info("+" * 78)

        self.parent.parameters["testbed"] = testbed

        for device in testbed.devices.values():
            log.info(f"Connecting to {device.name}...")
            device.connect(log_stdout=True)


# -----   Testcase: Deploy OSPF /31 Fabric  ---------

class DeployOSPF31Fabric(aetest.Testcase):
    """Deploy OSPF31 Fabric"""

    @property
    def testbed(self):
        return self.parent.parameters["testbed"]

    def _build_address_plan(self):
        """
        Return a mapping:
            (device, interface) -> (ip, mask)
        using sequential /31s from LINK_POOL.
        """
        addr_map = {}

        subnets = list(LINK_POOL.subnets(new_prefix=31))
        if len(subnets) < len(LINKS):
            self.failed(
                f"Not enough /31 subnets in pool {LINK_POOL} for {len(LINKS)} links"
            )

        for link, subnet in zip(LINKS, subnets):
            hosts = list(subnet.hosts())
            if len(hosts) != 2:
                # For /31, we expect exactly two usable addresses
                self.failed(f"Unexpected host count in {subnet}: {hosts}")

            ip_a, ip_b = hosts[0], hosts[1]
            mask = subnet.netmask

            (dev_a, intf_a), (dev_b, intf_b) = link["endpoints"]

            addr_map[(dev_a, intf_a)] = (str(ip_a), str(mask))
            addr_map[(dev_b, intf_b)] = (str(ip_b), str(mask))

        return addr_map

    def _build_device_configs(self, addr_map):
        """
        Build per-device config snippets for:
        - /31 IP addressing on the right interfaces
        - Interface-level OSPF in area 10

        Returns:
            {device_name: "config\nlines\n..."}
        """
        device_cfgs = {}

        for (dev_name, intf_name), (ip, mask) in addr_map.items():
            if dev_name not in device_cfgs:
                device_cfgs[dev_name] = []

            cfg_lines = device_cfgs[dev_name]
            cfg_lines.append(f"interface {intf_name}")
            cfg_lines.append(f" description {dev_name} {intf_name} - OSPF area {OSPF_AREA}")
            cfg_lines.append(f" ip address {ip} {mask}")
            cfg_lines.append(f" ip ospf {OSPF_PROCESS_ID} area {OSPF_AREA}")
            cfg_lines.append(" no shutdown")

        # Ensure OSPF process exists on each device
        for dev_name, cfg_lines in device_cfgs.items():
            cfg_lines.insert(0, f"router ospf {OSPF_PROCESS_ID}")
            # Optionally add router-id here
            # cfg_lines.insert(1, f"router-id 1.1.1.{some_id}")

        # Add Loopback0 interface and router-id
        for idx, dev_name in enumerate(sorted(device_cfgs.keys()), start=1):
            cfg_lines = device_cfgs[dev_name]
            loopback_ip = f"{idx}.{idx}.{idx}.{idx}"

            # Add Loopback0 interface config
            cfg_lines.insert(0, "interface Loopback0")
            cfg_lines.insert(1, f" ip address {loopback_ip} 255.255.255.255")
            cfg_lines.insert(2, f" ip ospf {OSPF_PROCESS_ID} area {OSPF_AREA}")
            cfg_lines.insert(3, " no shutdown")

            # Add router ospf block with router-id at the top
            cfg_lines.insert(4, f"router ospf {OSPF_PROCESS_ID}")
            cfg_lines.insert(5, f" router-id {loopback_ip}")

        # Join lines into a single string per device
        device_cfgs_str = {dev: "\n".join(lines) for dev, lines in device_cfgs.items()}
        return device_cfgs_str

    @aetest.test
    def deploy_ospf_31_fabric(self):
        """
        - Generate unique /31 addresses per link.
        - Build interface + OSPF config per device.
        - Push configs to the devices.
        """
        addr_map = self._build_address_plan()
        device_cfgs = self._build_device_configs(addr_map)

        all_ok = True

        for dev_name, cfg in device_cfgs.items():
            if dev_name not in self.testbed.devices:
                log.error(f"{dev_name} is referenced in topology but not in testbed.")
                all_ok = False
                continue

            device = self.testbed.devices[dev_name]

            log.info("+" * 78)
            log.info(f"|        Deploying OSPF /31 fabric config to {dev_name}        |")
            log.info("+" * 78)
            log.info(f"Config for {dev_name}:\n{cfg}")

            try:
                device.configure(cfg)
                log.info(f"Successfully applied OSPF /31 fabric config on {dev_name}")
            except Exception as e:
                log.error(f"Failed to configure {dev_name}: {e}")
                all_ok = False

        if all_ok:
            self.passed("OSPF /31 fabric deployed successfully on all devices")
        else:
            self.failed("One or more devices failed OSPF /31 deployment")


# ---- Common CLeanup ------------------

class CommonCleanup(aetest.CommonCleanup):
    """ Common Cleanup """

    @aetest.subsection
    def disconnect_from_testbed_(self):
        """Disconnect from all devices in the testbed."""

        log.info("+" * 78)
        log.info("|        Disconnecting from all devices in testbed                 |")
        log.info("+" * 78)

        testbed = self.parent.parameters["testbed"]

        if not testbed:
            log.warning("No testbed found in parent parameters; nothing to disconnect.")
            return

        for device in testbed.devices.values():
            if hasattr(device, "is_connected") and device.is_connected():
                log.info(f"Disconnecting from {device.name}...")
                try:
                    device.disconnect()
                except Exception as e:
                    log.warning(f"Error disconnecting from {device.name}: {e}")


import time
from genie.libs.parser.iosxe.show_ospf import ShowIpOspfNeighbor


class MonitorOSPFAdjacencies(aetest.Testcase):
    """Continuously Monitor OSPF Neighbor Adjacencies"""

    duration = 120  # Total duration to monitor (in seconds)
    interval = 30  # Interval between checks (in seconds)

    @property
    def testbed(self):
        return self.parent.parameters["testbed"]

    def _check_neighbors(self):
        all_ok = True

        for device in self.testbed.devices.values():
            try:
                log.info(f"Checking OSPF neighbors on {device.name}...")
                output = device.parse("show ip ospf neighbor")
                log.debug(f"OSPF Neighbor Output for {device.name}: {output}")
            except Exception as e:
                log.error(f"Error collecting OSPF data from {device.name}: {e}")
                all_ok = False
                continue

            neighbors = output.get("vrf", {}).get("default", {}) \
                .get("address_family", {}).get("ipv4", {}) \
                .get("instance", {})

            for _, instance in neighbors.items():
                for area in instance.get("areas", {}).values():
                    for neighbor in area.get("neighbors", {}).values():
                        rid = neighbor.get("neighbor_router_id", "Unknown")
                        state = neighbor.get("state", "unknown").lower()
                        if state != "full":
                            log.warning(f"Neighbor {rid} on {device.name} is in state {state}")
                            all_ok = False

        return all_ok

    @aetest.test
    def continuous_monitoring(self):
        """
        Periodically checks OSPF neighbor states over a duration.
        Logs warnings on any drops or incomplete adjacencies.
        """
        log.info(f"Monitoring OSPF neighbors every {self.interval}s for {self.duration}s")
        end_time = time.time() + self.duration
        issues_found = False

        while time.time() < end_time:
            check_result = self._check_neighbors()
            if not check_result:
                issues_found = True
            time.sleep(self.interval)

        if not issues_found:
            self.passed(f"No OSPF neighbor issues detected in {self.duration} seconds.")
        else:
            self.failed("Detected one or more OSPF neighbor issues during monitoring.")