# 🌐 PyATS OSPF Testing Lab

Automated network testing suite using Cisco pyATS for OSPF deployment, verification, and resilience testing.

---

## 📋 Overview

This lab demonstrates a complete network automation workflow:

1. **Connectivity Testing** - Verify device reachability
2. **OSPF Deployment** - Configure OSPF with /31 point-to-point links
3. **Data Export** - Collect network state to JSON
4. **Resilience Testing** - Flap interfaces and measure convergence
5. **Reset** - Clear configuration for re-testing

All scripts use **parallel connections** for scalability (tested with 4 devices, scales to 50+).

---

## 🖥️ Network Topology

```
                    10.0.0.0/31
              Gi0/1 ←────────→ Gi0/1
         ┌────────────────────────────┐
         │                            │
        R1                           R2
     (1.1.1.1)                    (2.2.2.2)
         │                            │
         │ Gi0/2                Gi0/2 │
         │ 10.0.0.2/31    10.0.0.4/31 │
         │                            │
         │ Gi0/2                Gi0/2 │
         │                            │
        R4                           R3
     (4.4.4.4)                    (3.3.3.3)
         │                            │
         └────────────────────────────┘
              Gi0/1 ←────────→ Gi0/1
                    10.0.0.6/31
```

### IP Addressing

| Link | Router | Interface | IP Address |
|------|--------|-----------|------------|
| R1-R2 | R1 | Gi0/1 | 10.0.0.0/31 |
| R1-R2 | R2 | Gi0/1 | 10.0.0.1/31 |
| R1-R4 | R1 | Gi0/2 | 10.0.0.2/31 |
| R1-R4 | R4 | Gi0/2 | 10.0.0.3/31 |
| R2-R3 | R2 | Gi0/2 | 10.0.0.4/31 |
| R2-R3 | R3 | Gi0/2 | 10.0.0.5/31 |
| R3-R4 | R3 | Gi0/1 | 10.0.0.6/31 |
| R3-R4 | R4 | Gi0/1 | 10.0.0.7/31 |

### Loopbacks

| Router | Loopback0 |
|--------|-----------|
| R1 | 1.1.1.1/32 |
| R2 | 2.2.2.2/32 |
| R3 | 3.3.3.3/32 |
| R4 | 4.4.4.4/32 |

---

## 📁 File Structure

```
pyats_labs/
├── testbeds/
│   └── testbed.yaml                    # Device inventory
├── results/                            # Test output directory
│
├── # TEST SCRIPTS
├── connectivity_test_scalable.py       # Connectivity verification
├── deploy_ospf_31_enhanced_scalable.py # OSPF deployment
├── ospf_export_test_scalable.py        # Data export to JSON
├── ospf_flap_test_advanced_scalable.py # Resilience testing
├── reset_ospf_config.py                # Configuration reset
│
├── # JOB FILES
├── connectivity_test_scalable_job.py
├── deploy_ospf_31_enhanced_scalable_job.py
├── export_ospf_detailed_json_scalable.py
├── ospf_flap_job_advanced_scalable.py
├── reset_ospf_job.py
│
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install pyATS
pip install pyats[full] genie
```

### Run Complete Workflow

```bash
# 1. Verify connectivity
pyats run job connectivity_test_scalable_job.py --testbed-file testbeds/testbed.yaml

# 2. Deploy OSPF configuration
pyats run job deploy_ospf_31_enhanced_scalable_job.py --testbed-file testbeds/testbed.yaml

# 3. Export network data
pyats run job export_ospf_detailed_json_scalable.py --testbed-file testbeds/testbed.yaml

# 4. Run resilience tests
pyats run job ospf_flap_job_advanced_scalable.py --testbed-file testbeds/testbed.yaml

# 5. Reset for next test (optional)
pyats run job reset_ospf_job.py --testbed-file testbeds/testbed.yaml
```

---

## 📝 Script Details

### 1. Connectivity Test (`connectivity_test_scalable.py`)

**Purpose:** Verify management connectivity to all devices

**What it does:**
- Connects to all devices in parallel
- Parses `show ip interface brief`
- Verifies GigabitEthernet0/0 has an IP address
- Generates `interface_report.txt`

**Run:**
```bash
pyats run job connectivity_test_scalable_job.py --testbed-file testbeds/testbed.yaml
cat interface_report.txt
```

---

### 2. OSPF Deploy (`deploy_ospf_31_enhanced_scalable.py`)

**Purpose:** Deploy complete OSPF configuration with point-to-point links

**What it does:**
- Connects to all devices in parallel
- Configures Loopback0 on each router
- Configures Gi0/1 and Gi0/2 with /31 IPs
- Sets `ip ospf network point-to-point` (RFC 3021)
- Enables OSPF process 10, area 10
- Verifies OSPF neighbors reach FULL state
- Confirms point-to-point mode (`FULL/-` not `FULL/DR`)

**Key Configuration:**
```
interface GigabitEthernet0/1
 ip address 10.0.0.X 255.255.255.254
 ip ospf network point-to-point
 no shutdown

router ospf 10
 router-id X.X.X.X
 network X.X.X.X 0.0.0.0 area 10
```

**Run:**
```bash
pyats run job deploy_ospf_31_enhanced_scalable_job.py --testbed-file testbeds/testbed.yaml
```

---

### 3. Data Export (`ospf_export_test_scalable.py`)

**Purpose:** Collect complete network state and export to JSON

**What it does:**
- Connects to all devices in parallel
- Collects in parallel from each device:
  - `show ip ospf neighbor`
  - `show ip ospf interface brief`
  - `show ip interface brief`
  - `show ip route ospf`
  - Loopback addresses
- Generates JSON files:
  - `ospf_complete_export.json` - Full data
  - `network_topology.json` - Nodes and links
  - `export_summary.json` - Quick reference

**Run:**
```bash
pyats run job export_ospf_detailed_json_scalable.py --testbed-file testbeds/testbed.yaml
cat results/ospf_export_*/export_summary.json
```

---

### 4. Flap Test (`ospf_flap_test_advanced_scalable.py`)

**Purpose:** Test OSPF resilience by flapping interfaces and measuring convergence

**What it does:**
- Connects to all devices in parallel
- For each configured interface:
  1. Captures baseline OSPF neighbors
  2. Shuts down interface (5 seconds)
  3. Verifies neighbor goes down
  4. Brings interface back up
  5. Measures convergence time (polls every 0.5s)
  6. Compares final state to baseline
- Generates `flap_test_results.json` with:
  - Pass/fail for each interface
  - Convergence times
  - SLA compliance (target: 10 seconds)

**Configuration:**
```python
TEST_CONFIGS = [
    {'device': 'R1', 'interface': 'GigabitEthernet0/1'},
    {'device': 'R1', 'interface': 'GigabitEthernet0/2'},
]
SLA_TARGET = 10.0  # seconds
```

**Run:**
```bash
pyats run job ospf_flap_job_advanced_scalable.py --testbed-file testbeds/testbed.yaml
cat results/ospf_flap_*/flap_test_results.json
```

---

### 5. Reset (`reset_ospf_config.py`)

**Purpose:** Clear all OSPF and interface configuration for re-testing

**What it removes:**
- `no router ospf 10`
- `no ip address` on Gi0/1 and Gi0/2
- `shutdown` on Gi0/1 and Gi0/2
- `no interface Loopback0`

**Run:**
```bash
pyats run job reset_ospf_job.py --testbed-file testbeds/testbed.yaml
```

---

## ⚡ Key Features

### Parallel Connections

All scripts use `ThreadPoolExecutor` for parallel device connections:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=10) as executor:
    futures = {executor.submit(connect_one, d): d for d in testbed.devices.values()}
    for future in as_completed(futures):
        name, success, error = future.result()
```

**Performance:**
| Devices | Sequential | Parallel |
|---------|-----------|----------|
| 4 | ~20 sec | ~6 sec |
| 50 | ~4 min | ~30 sec |
| 100 | ~8 min | ~60 sec |

### Point-to-Point OSPF (RFC 3021)

Using `/31` subnets with `ip ospf network point-to-point`:
- ✅ No DR/BDR elections
- ✅ Faster convergence
- ✅ Consistent neighbor state (`FULL/-` not `FULL/DR`)
- ✅ Efficient IP address usage

---

## 📊 Expected Results

### Successful OSPF Deployment
```
R1 → 2.2.2.2: FULL/  - via GigabitEthernet0/1
R1 → 4.4.4.4: FULL/  - via GigabitEthernet0/2
R2 → 1.1.1.1: FULL/  - via GigabitEthernet0/1
R2 → 3.3.3.3: FULL/  - via GigabitEthernet0/2
...
```

### Successful Flap Test
```json
{
  "summary": {
    "total_tests": 2,
    "passed": 2,
    "failed": 0,
    "average_convergence": "8.25s",
    "sla_target": "10.0s",
    "sla_met": true
  }
}
```

---

## 🔧 Testbed Configuration

Example `testbeds/testbed.yaml`:

```yaml
testbed:
  name: OSPF_Lab

devices:
  R1:
    os: iosxe
    type: router
    connections:
      default:
        protocol: ssh
        ip: 192.168.68.71
    credentials:
      default:
        username: admin
        password: admin

  R2:
    os: iosxe
    type: router
    connections:
      default:
        protocol: ssh
        ip: 192.168.68.51
    credentials:
      default:
        username: admin
        password: admin

  # ... R3, R4
```

---

## 🐛 Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `No testbed provided!` | Typo in command | Check `--testbed-file` spelling |
| `Parser Output is empty` | No OSPF neighbors | Run deploy script first |
| `Connection timeout` | Device unreachable | Check IP/credentials in testbed.yaml |
| `BLOCKED` tests | CommonSetup failed | Fix the connection issue first |

---

## 📚 Resources

- [pyATS Documentation](https://developer.cisco.com/docs/pyats/)
- [Genie Parsers](https://pubhub.devnetcloud.com/media/genie-feature-browser/docs/#/)
- [RFC 3021 - /31 Point-to-Point Links](https://tools.ietf.org/html/rfc3021)

---

## 📄 License

MIT License - Feel free to use and modify for your own labs!