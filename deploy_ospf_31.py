from pyats import aetest
from ipaddress import ip_network
import logging

log = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Topology Description
# -----------------------------------------------------------------------------

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

# Base pool to carve /31s from
LINK_POOL = ip_network("10.0.0.0/24")
OSPF_PROCESS_ID = 10
OSPF_AREA = 10

# Loopback intent: /32s per router
LOOPBACKS = {
    "R1": "1.1.1.1",
    "R2": "2.2.2.2",
    "R3": "3.3.3.3",
    "R4": "4.4.4.4",
}


# -----------------------------------------------------------------------------
# Common Setup
# -----------------------------------------------------------------------------

class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def connect_to_testbed(self, testbed):
        """Connect to all devices defined in the testbed."""
        log.info("+" * 78)
        log.info("|             Loading testbed and connecting to all devices...              |")
        log.info("+" * 78)

        self.parent.parameters["testbed"] = testbed

        for device in testbed.devices.values():
            log.info(f"Connecting to {device.name}...")
            device.connect(log_stdout=True)


# -----------------------------------------------------------------------------
# Testcase: Deploy OSPF /31 Fabric + Loopbacks
# -----------------------------------------------------------------------------

class DeployOSPF31Fabric(aetest.Testcase):

    @property
    def testbed(self):
        return self.parent.parameters["testbed"]

    def _build_address_plan(self):
        """
        Build a mapping:
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
          - /31 IP addressing on P2P interfaces
          - Interface-level OSPF in area 10
          - Loopback0 with /32 and OSPF in area 10

        Returns:
          { device_name: "config\nlines\n..." }
        """
        device_cfgs = {}

        # P2P interfaces
        for (dev_name, intf_name), (ip, mask) in addr_map.items():
            if dev_name not in device_cfgs:
                device_cfgs[dev_name] = []

            cfg_lines = device_cfgs[dev_name]

            cfg_lines.append(f"interface {intf_name}")
            cfg_lines.append(
                f" description {dev_name} {intf_name} - OSPF area {OSPF_AREA}"
            )
            cfg_lines.append(f" ip address {ip} {mask}")
            cfg_lines.append(f" ip ospf {OSPF_PROCESS_ID} area {OSPF_AREA}")
            cfg_lines.append(" no shutdown")

        # Loopbacks
        for dev_name, lo_ip in LOOPBACKS.items():
            if dev_name not in device_cfgs:
                device_cfgs[dev_name] = []
            cfg_lines = device_cfgs[dev_name]

            cfg_lines.append("interface Loopback0")
            cfg_lines.append(f" description {dev_name} Loopback0 - OSPF loopback")
            cfg_lines.append(f" ip address {lo_ip} 255.255.255.255")
            cfg_lines.append(f" ip ospf {OSPF_PROCESS_ID} area {OSPF_AREA}")
            cfg_lines.append(" no shutdown")

        # Ensure OSPF process exists on each device
        for dev_name, cfg_lines in device_cfgs.items():
            cfg_lines.insert(0, f"router ospf {OSPF_PROCESS_ID}")
            # Optional: set explicit router-id here if you want
            # cfg_lines.insert(1, f" router-id {LOOPBACKS.get(dev_name, '1.1.1.1')}")

        # Join lines into a single string per device
        device_cfgs_str = {dev: "\n".join(lines) for dev, lines in device_cfgs.items()}
        return device_cfgs_str

    @aetest.test
    def deploy_ospf_31_fabric(self):
        """
        - Generate unique /31 addresses per P2P link.
        - Configure P2P interfaces + OSPF.
        - Create Loopback0 on each device and add it to OSPF area 10.
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
            log.info(f"|   Deploying OSPF /31 fabric + Loopback0 config to {dev_name}           |")
            log.info("+" * 78)
            log.info(f"Config for {dev_name}:\n{cfg}")

            try:
                device.configure(cfg)
                log.info(
                    f"Successfully applied OSPF /31 fabric + Loopback0 config on {dev_name}"
                )
            except Exception as e:
                log.error(f"Failed to configure {dev_name}: {e}")
                all_ok = False

        if all_ok:
            self.passed("OSPF /31 fabric and loopbacks deployed successfully")
        else:
            self.failed("One or more devices failed OSPF /31 + loopback deployment")


# -----------------------------------------------------------------------------
# Common Cleanup
# -----------------------------------------------------------------------------

class CommonCleanup(aetest.CommonCleanup):
    @aetest.subsection
    def disconnect_from_testbed(self):
        """Disconnect from all devices in the testbed."""
        log.info("+" * 78)
        log.info("|                  Disconnecting from all devices in testbed               |")
        log.info("+" * 78)

        testbed = self.parent.parameters.get("testbed")

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
