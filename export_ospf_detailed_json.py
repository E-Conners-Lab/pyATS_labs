import json
from genie.testbed import load

def collect_detailed_ospf_data(testbed_file, output_file):
    testbed = load(testbed_file)
    ospf_data = {}

    for device in testbed.devices.values():
        print(f"Connecting to {device.name}...")
        try:
            device.connect(log_stdout=False)
        except Exception as e:
            print(f"❌ Failed to connect to {device.name}: {e}")
            continue

        device_data = {
            "non_mgmt_interfaces": {},
            "loopback0": None,
            "ospf_neighbor_output": "",
            "ospf_interface_brief_output": ""
        }

        try:
            parsed_ints = device.parse("show ip interface brief")
            for intf, info in parsed_ints.get("interface", {}).items():
                ip = info.get("ip_address", "")
                if "Loopback0" in intf:
                    device_data["loopback0"] = ip
                elif "GigabitEthernet0/1" in intf or "GigabitEthernet0/2" in intf:
                    device_data["non_mgmt_interfaces"][intf] = ip
        except Exception as e:
            print(f"⚠️ Failed to parse interfaces on {device.name}: {e}")

        try:
            device_data["ospf_interface_brief_output"] = device.execute("show ip ospf interface brief")
        except Exception as e:
            print(f"⚠️ Failed to collect OSPF interface brief on {device.name}: {e}")

        try:
            device_data["ospf_neighbor_output"] = device.execute("show ip ospf neighbor")
        except Exception as e:
            print(f"⚠️ Failed to collect OSPF neighbors on {device.name}: {e}")

        ospf_data[device.name] = device_data
        device.disconnect()

    with open(output_file, "w") as f:
        json.dump(ospf_data, f, indent=2)

    print(f"✅ Data exported to {output_file}")

if __name__ == "__main__":
    collect_detailed_ospf_data("testbeds/testbed.yaml", "ospf_detailed_export.json")
