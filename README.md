# Network Automation with pyATS: Interface Validation & OSPF Deployment

This repository contains two modular test scripts using Cisco's [pyATS](https://developer.cisco.com/pyats/) and Genie libraries. These scripts automate interface health checks and deploy a fully-connected OSPF /31 fabric, complete with loopback setup and neighbor adjacency monitoring.

---

## 🔍 1. Interface Connectivity Check (`connectivity_test.py`)

This script performs an initial health check across all routers by validating that `GigabitEthernet0/0` has a configured IP address.

### ✅ What it Does:
- Connects to all devices in the testbed.
- Runs `show ip interface brief`.
- Parses output with Genie to validate `GigabitEthernet0/0`.
- Logs results and generates a report (`interface_report.txt`).
- Cleanly disconnects from all devices on completion.

### 📄 Report Example:
```text
Interface IP Check Report

R1 - GigabitEthernet0/0 IP is 10.0.0.1
R2 - GigabitEthernet0/0 has no IP address
R3 - GigabitEthernet0/0 not found in parsed output
R4 - GigabitEthernet0/0 IP is 10.0.0.4
```

---

## 🔧 2. OSPF /31 Fabric Deployment & Monitoring (`deploy_ospf_31.py`)

After confirming device readiness, this script builds a dynamic OSPF fabric using /31 point-to-point links and loopback addresses.

### ✅ What it Does:
- Builds an address plan from a `/24` pool to carve `/31` subnets.
- Assigns IP addresses to link interfaces across devices.
- Creates `Loopback0` with IPs like `1.1.1.1`, `2.2.2.2`, etc.
- Sets the OSPF `router-id` to the device’s loopback IP.
- Advertises both loopback and P2P interfaces in OSPF area 10.
- Deploys all configurations via `device.configure()`.

### 👁️ OSPF Adjacency Monitoring:
- Periodically checks `show ip ospf neighbor` using Genie.
- Verifies that neighbors reach the `FULL` state.
- Runs for 2 minutes (check every 30 seconds).
- Fails the test if any adjacency drops or becomes unstable.

---

## 🧪 Project Structure

```text
.
├── connectivity_test.py        # Interface validation using Genie
├── deploy_ospf_31.py           # OSPF /31 deployment and monitoring
├── interface_report.txt        # Auto-generated IP address report
├── testbeds/
│   └── testbed.yaml            # pyATS testbed file with device definitions
└── README.md                   # Project documentation
```

---

## ⚙️ Requirements

- Python 3.8+
- pyATS & Genie libraries
- Reachable Cisco devices
- Completed `testbed.yaml`

Install with:

```bash
pip install 'pyats[full]'
```

---

## 🚀 Running the Scripts

Run each script using a job file or directly with `pyats run job`:

```bash
pyats run job connectivity_test_job.py --testbed-file testbeds/testbed.yaml
pyats run job deploy_ospf_31_job.py --testbed-file testbeds/testbed.yaml
```

---

## 🧭 Roadmap & Extensibility

You can expand this project to:
- Validate routing tables (`show ip route`)
- Ping between loopbacks across devices
- Generate Markdown/CSV/HTML reports
- Integrate into CI/CD pipelines for automated lab tests

---

## 📜 License

MIT License

---

## 🤝 Contributions

PRs and feedback welcome — let’s build a more extensible pyATS test suite together.
