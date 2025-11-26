# ospf_flap_trigger.py

from pyats.aetest import Testcase, test, loop
from genie.libs.sdk.triggers.base import Trigger
from genie.libs.sdk.libs.utils.mapping import Mapping
from genie.libs.parser.utils.common import get_interface_type


class TriggerFlapOspfInterface(Trigger):
    """Flap an interface running OSPF and verify adjacency re-forms"""

    __description__ = """Flap OSPF-enabled interface and verify neighbor adjacency returns"""

    # Mapping of requirements, config info, verification steps
    mapping = Mapping.requirements.insert(
        ospf=('ops.ospf.ospf.Ospf', 'info', {
            'vrf': {
                'default': {
                    'address_family': {
                        'ipv4': {
                            'instance': {
                                '': {
                                    'areas': {
                                        '': {
                                            'interfaces': {
                                                '': {
                                                    'neighbors': {
                                                        '': {
                                                            'state': 'full'
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        })
    ).configure(None).verify_ops(
        ospf=('ops.ospf.ospf.Ospf', 'info', {
            'vrf': {
                'default': {
                    'address_family': {
                        'ipv4': {
                            'instance': {
                                '': {
                                    'areas': {
                                        '': {
                                            'interfaces': {
                                                '': {
                                                    'neighbors': {
                                                        '': {
                                                            'state': 'full'
                                                        }
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        })
    ).value_also_match('interface')

    def configure(self, device, abstract, steps, interfaces, **kwargs):
        intf = interfaces[0]
        with steps.start("Shutdown interface {}".format(intf)):
            device.configure([
                "interface {}".format(intf),
                "shutdown"
            ])
        device.sleep(5)
        with steps.start("Bring interface {} back up".format(intf)):
            device.configure([
                "interface {}".format(intf),
                "no shutdown"
            ])
        device.sleep(10)
