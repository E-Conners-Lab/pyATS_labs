import time
import logging

from pyats import aetest
from genie.harness.base import Trigger
from genie.metaparser.util.exceptions import SchemaEmptyParserError

log = logging.getLogger(__name__)


class MyShutNoShutOspf(Trigger):
    """Shut/no shut the OSPF process and verify both actions.

    Notes:
      - This flaps the *OSPF process*, not interfaces.
      - If OSPF isn't configured/enabled, the trigger is skipped for that device.
    """

    @aetest.setup
    def prerequisites(self, uut):
        """Ensure OSPF is present and learn the local OSPF process-id."""
        try:
            output = uut.parse("show ip ospf")
        except SchemaEmptyParserError:
            self.skipped(f"OSPF is not configured on device {uut.name}")
            return

        instances = (
            output.get("vrf", {})
            .get("default", {})
            .get("address_family", {})
            .get("ipv4", {})
            .get("instance", {})
        )

        if not instances:
            self.skipped(f"No OSPF instances found on device {uut.name}")
            return

        # Use the first process-id found
        self.ospf_id = list(instances.keys())[0]

        # Missing 'enable' on some platforms; default to True if absent
        ospf_enabled = instances.get(self.ospf_id, {}).get("enable", True)
        if not ospf_enabled:
            self.skipped(f"OSPF process {self.ospf_id} is not enabled on device {uut.name}")
            return

        log.info(f"[{uut.name}] Using OSPF process-id: {self.ospf_id}")

    @aetest.test
    def ShutOspf(self, uut):
        """Shutdown the OSPF process."""
        uut.configure([f"router ospf {self.ospf_id}", "shutdown"])
        time.sleep(5)

    @aetest.test
    def verify_ShutOspf(self, uut):
        """Verify OSPF is shut."""
        output = uut.parse("show ip ospf")
        enabled = (
            output.get("vrf", {})
            .get("default", {})
            .get("address_family", {})
            .get("ipv4", {})
            .get("instance", {})
            .get(self.ospf_id, {})
            .get("enable", True)
        )
        if enabled:
            self.failed(f"OSPF is still enabled on {uut.name}")

    @aetest.test
    def NoShutOspf(self, uut):
        """Unshut the OSPF process."""
        uut.configure([f"router ospf {self.ospf_id}", "no shutdown"])
        time.sleep(5)

    @aetest.test
    def verify_NoShutOspf(self, uut):
        """Verify OSPF is back up."""
        output = uut.parse("show ip ospf")
        enabled = (
            output.get("vrf", {})
            .get("default", {})
            .get("address_family", {})
            .get("ipv4", {})
            .get("instance", {})
            .get(self.ospf_id, {})
            .get("enable", False)
        )
        if not enabled:
            self.failed(f"OSPF is NOT enabled on {uut.name}")
