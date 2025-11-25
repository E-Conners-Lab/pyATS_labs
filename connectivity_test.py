from pyats import aetest
import logging

log = logging.getLogger(__name__)


class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def connect_to_testbed(self, testbed):
        """Connect to all devices defined in the testbed."""
        log.info("+" * 78)
        log.info("|               Loading testbed and connecting to all devices...               |")
        log.info("+" * 78)

        # Store the testbed so testcases and cleanup can reuse it
        self.parent.parameters["testbed"] = testbed

        for device in testbed.devices.values():
            log.info(f"Connecting to {device.name}...")
            device.connect(log_stdout=True)


class ConnectivityTest(aetest.Testcase):
    """Testcase that verifies interface IP addressing on all devices."""

    @property
    def testbed(self):
        """Convenience accessor for the shared testbed."""
        return self.parent.parameters["testbed"]

    def _check_g0_interface(self, device):
        """
        Check GigabitEthernet0/0 on a single device.

        Returns:
            (passed: bool, message: str)
        """
        log.info("+" * 78)
        log.info(f"|                        Parsing interface data for {device.name}                         |")
        log.info("+" * 78)

        try:
            parsed = device.parse("show ip interface brief")
            log.debug(f"{device.name} parsed 'show ip interface brief': {parsed}")
        except Exception as e:
            msg = f"{device.name} - Error while parsing interface: {e}"
            log.exception(msg)
            return False, msg

        # Safely navigate the parsed structure
        interfaces = parsed.get("interface", {})
        g0 = interfaces.get("GigabitEthernet0/0")

        if not g0:
            msg = f"{device.name} - GigabitEthernet0/0 not found in parsed output"
            return False, msg

        ip_addr = g0.get("ip_address")

        if not ip_addr or ip_addr == "unassigned":
            msg = f"{device.name} - GigabitEthernet0/0 has no IP address"
            return False, msg

        msg = f"{device.name} - GigabitEthernet0/0 IP is {ip_addr}"
        return True, msg

    @aetest.test
    def check_interfaces(self):
        """
        Run the IP address check on GigabitEthernet0/0 for all devices
        and write results to interface_report.txt.
        """
        report_lines = ["Interface IP Check Report", ""]
        all_passed = True

        for device in self.testbed.devices.values():
            passed, message = self._check_g0_interface(device)

            if passed:
                log.info(message)
            else:
                log.error(message)
                all_passed = False

            report_lines.append(message)

        # Write the report in one shot
        with open("interface_report.txt", "w") as report_file:
            report_file.write("\n".join(report_lines) + "\n")

        if all_passed:
            self.passed("All interfaces checked successfully")
        else:
            self.failed("One or more interface checks failed")


class CommonCleanup(aetest.CommonCleanup):
    @aetest.subsection
    def disconnect_from_testbed(self):
        """Disconnect from all devices in the testbed."""
        log.info("+" * 78)
        log.info("|                  Disconnecting from all devices in testbed                  |")
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
