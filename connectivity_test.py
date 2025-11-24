from pyats import aetest
import logging
from genie.testbed import load

log = logging.getLogger(__name__)

class CommonSetup(aetest.CommonSetup):
    @aetest.subsection
    def connect_to_testbed(self, testbed):
        log.info("+" * 78)
        log.info("|               Loading testbed and connecting to all devices...               |")
        log.info("+" * 78)

        self.parent.parameters['testbed'] = testbed

        for device in testbed.devices.values():
            log.info(f"Connecting to {device.name}...")
            device.connect(log_stdout=True)


class ConnectivityTest(aetest.Testcase):
    @aetest.setup
    def setup(self, testbed):
        self.testbed = testbed

    @aetest.test
    def connect_and_check_interface(self):
        report_lines = ["Interface IP Check Report\n"]
        all_passed = True

        for device in self.testbed.devices.values():
            log.info("+" * 78)
            log.info(f"|                        Parsing interface data for {device.name}                         |")
            log.info("+" * 78)

            try:
                intf = device.parse("show ip interface brief")
                log.info(f"{device.name} interface brief:\n{intf}")

                g0 = intf.get('interface', {}).get('GigabitEthernet0/0')

                if g0 is None:
                    result = f"{device.name} - GigabitEthernet0/0 not found in parsed output"
                    log.error(result)
                    report_lines.append(result)
                    all_passed = False
                    continue

                elif not g0['ip_address'] or g0['ip_address'] == 'unassigned':
                    result = f"{device.name} - GigabitEthernet0/0 has no IP address"
                    log.error(result)
                    report_lines.append(result)
                    all_passed = False
                    continue

                else:
                    result = f"{device.name} - GigabitEthernet0/0 IP is {g0['ip_address']}"
                    log.info(result)
                    report_lines.append(result)

            except Exception as e:
                result = f"{device.name} - Error while parsing interface: {e}"
                log.exception(result)
                report_lines.append(result)
                all_passed = False

        # Write results to file
        with open("interface_report.txt", "w") as report_file:
            for line in report_lines:
                report_file.write(line + "\n")

        if all_passed:
            self.passed("All interfaces checked successfully")
        else:
            self.failed("One or more interface checks failed")
