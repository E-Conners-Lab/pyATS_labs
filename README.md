# OSPF pyATS Automation Suite

This project automates the deployment, verification, and export of OSPF configuration and status across a multi-router lab environment using Cisco pyATS.

## 🔧 Files Overview

### 1. `connectivity_test.py`
- **Purpose:** Initial validation of connectivity.
- **Checks:** Confirms that all devices in the testbed have an IP address assigned to their `GigabitEthernet0/0` interfaces.
- **Output:** `interface_report.txt` with status per device.

### 2. `deploy_ospf_31.py`
- **Purpose:** Fully configures a simulated OSPF network with /31 point-to-point links.
- **Features:**
  - Assigns IPs using a /31 subnet pool.
  - Builds OSPF configuration including `Loopback0` and router IDs.
  - Advertises only the loopbacks into OSPF.
  - Includes a monitoring test that validates OSPF neighbor adjacencies for 2 minutes.

### 3. `export_ospf_detailed_json.py`
- **Purpose:** Collects and exports detailed OSPF state and interface data into a structured JSON file.
- **Captured Data:**
  - IP addresses of `GigabitEthernet0/1` and `GigabitEthernet0/2` (non-management)
  - `Loopback0` IP address
  - Raw CLI output from:
    - `show ip ospf interface brief`
    - `show ip ospf neighbor`
- **Output:** `ospf_detailed_export.json`

## 📦 Requirements
- Python 3.8+
- pyATS & Genie libraries
- Valid `testbed.yaml` in `testbeds/` folder

## ▶️ How to Use

### Run Initial Connectivity Test
```bash
python connectivity_test.py
```

### Deploy OSPF /31 Topology
```bash
pyats run job deploy_ospf_31.py --testbed-file testbeds/testbed.yaml
```

### Export OSPF State as JSON
```bash
python export_ospf_detailed_json.py
```

## 📊 Use Cases
- Automated OSPF deployment and validation
- Network state reporting and documentation
- JSON-driven visualization using tools like Mermaid or Grafana

---

**Author:**  Elliot Conner  
**Updated:** 2025-11-25
