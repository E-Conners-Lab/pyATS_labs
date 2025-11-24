from genie.testbed import load

# Load the testbed YAML relative to the project root
tb= load("testbeds/lab_testbed.yaml")

print("Loaded testbed:", tb.name)
print("Devices in testbed:", list(tb.devices.keys()))

# Grab one device object just to show it's there
r1 = tb.devices["R1"]
print("R1 object:", r1)

