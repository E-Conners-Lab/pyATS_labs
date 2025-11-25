# pyATS Connectivity Interface Check

This project is a small but complete **pyATS / Genie** lab that connects to a testbed, runs a basic health check, cleans up connections, and writes the results to a report file. It’s meant as a starting point for building out more advanced network automation and testing workflows.

---

## Project Overview

The core test script (`connectivity_test.py`) now includes: 

- A **CommonSetup** section that:
  - Receives the pyATS / Genie testbed from the job.
  - Connects to every device in the testbed and stores the shared `testbed` object for reuse.
- A **ConnectivityTest** testcase that:
  - Parses `show ip interface brief` using Genie for each device.
  - Verifies that **GigabitEthernet0/0** has a configured IP address.
  - Logs results and writes a summary to `interface_report.txt`.
- A **CommonCleanup** section that:
  - Iterates over the same `testbed`.
  - Cleanly disconnects from all devices at the end of the run.

This structure separates setup, testing, and cleanup clearly, and matches how larger pyATS test suites are typically organized.

---

## Repository Structure

```text
pyats_labs/
├── connectivity_test.py        # AEtest script: setup, test, and cleanup for interface checks
├── connectivity_test_job.py    # easypy job: runs the testscript
├── testbeds/
│   └── testbed.yaml            # pyATS testbed definition (your devices)
├── interface_report.txt        # Generated test report (output)
└── README.md                   # Project documentation
```

> Note: `interface_report.txt` is created/overwritten each time the test runs.

---

## Prerequisites

- Python 3.8+ (virtual environment recommended)
- pyATS and Genie libraries
- Network devices reachable from your machine (physical lab or EVE-NG)
- Valid `testbed.yaml` file describing your devices

Install pyATS & Genie (one simple way):

```bash
pip install "pyats[full]"
```

Or, if you prefer a smaller footprint, install only the pyATS / Genie components you need.

---

## Setup

1. **Clone the repo** (or copy these files into your existing `pyats_labs` project).

2. **Create & activate a virtual environment** (optional but recommended):

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   # .venv\Scripts\activate     # Windows
   ```

3. **Install dependencies**:

   ```bash
   pip install "pyats[full]"
   ```

4. **Confirm your testbed file**:

   - Place your `testbed.yaml` in the `testbeds/` directory.
   - Make sure device names and connection details match your lab (IP, port, username/password, etc.).

In the example lab, the testbed defines four Cisco IOS XE routers (R1–R4) reachable via SSH on a management subnet.

---

## Running the Tests

From the project root (where `connectivity_test_job.py` lives), run:

```bash
pyats run job connectivity_test_job.py --testbed-file testbeds/testbed.yaml
```

pyATS will:

1. Start an easypy job.
2. Load your testbed.
3. Run `connectivity_test.py` (CommonSetup → ConnectivityTest → CommonCleanup).
4. Generate `interface_report.txt` in the current working directory.
5. Disconnect from all devices when the tests are complete.

---

## What the Test Actually Does

For each device in the testbed, `ConnectivityTest`:

1. **Connects via CommonSetup** using the connection info from `testbed.yaml`.
2. Issues `show ip interface brief`.
3. Uses **Genie parsers** to convert the output into structured data.
4. Looks for **GigabitEthernet0/0**:
   - If the interface is missing → marks as failure.
   - If the IP address is `unassigned` or empty → marks as failure.
   - Otherwise → records the IP address as a success.
5. Appends a line to `interface_report.txt` summarizing the result.

Example lines in `interface_report.txt` might look like:

```text
Interface IP Check Report

R1 - GigabitEthernet0/0 IP is 10.0.0.1
R2 - GigabitEthernet0/0 has no IP address
R3 - GigabitEthernet0/0 not found in parsed output
R4 - GigabitEthernet0/0 IP is 10.0.0.4
```

At the end of the test:

- If **all** devices pass, the testcase is marked as **PASSED**.
- If **any** device fails, the testcase is marked as **FAILED**.
- The **CommonCleanup** section disconnects from all devices defined in the testbed.

---

## Connection Lifecycle

The script follows a clear connection lifecycle:

1. **CommonSetup**  
   - Receives `testbed` from the job.
   - Connects to all devices.
   - Stores `testbed` on `self.parent.parameters` for shared use.

2. **ConnectivityTest**  
   - Accesses the same shared `testbed`.
   - Performs all parsing and validation work.
   - Writes the consolidated `interface_report.txt`.

3. **CommonCleanup**  
   - Reads `testbed` from shared parameters.
   - Disconnects from any device that is still connected.
   - Logs any disconnection errors without failing the entire job.

This pattern scales well as you add more testcases because the setup and cleanup logic remains centralized.

---

## Customizing the Script

You can easily extend `connectivity_test.py` to:

- Check **different interfaces** (for example, `GigabitEthernet0/1` or loopbacks).
- Validate additional properties (administrative/operational status, descriptions, etc.).
- Run **other show commands** and parse them with Genie (for example, `show ip route`, `show version`).
- Write richer reports (CSV, Markdown, JSON) for later processing.
- Add additional testcases that reuse the same CommonSetup/CommonCleanup.

High-level steps to customize:

1. Change the targeted interface name in the `_check_g0_interface()` helper.
2. Add more logic to inspect additional fields from the parsed output.
3. Add extra sections to the report file for different checks or devices.
4. Create new testcases that call similar helper methods but check different aspects of device health.

---

## Troubleshooting

**1. No devices connect**

- Check IP addresses and credentials in `testbed.yaml`.
- Verify that SSH is enabled on the devices.
- Confirm you can SSH manually from your host.

**2. Parser errors (Genie)**

- Make sure the device OS and platform in `testbed.yaml` are correct.
- Confirm that the command output matches what Genie expects (version / OS compatibility).
- Upgrade pyATS / Genie if you are on a very old release.

**3. `GigabitEthernet0/0` not found**

- Interface naming in your platform might differ (for example, `GigabitEthernet1` or `GigabitEthernet0/1`).
- Update the interface key in the script to match actual names on your devices.

---

## Roadmap / Next Steps

Ideas for where to take this next:

- Check multiple interfaces per device.
- Validate loopbacks and management interfaces.
- Include reachability tests (pings) between devices.
- Generate HTML or Markdown reports for GitHub or wikis.
- Integrate with CI/CD (run pyATS jobs automatically on changes).
- Add pre/post-change validation for configuration deployments.
- Extend the cleanup phase to remove temporary files or artifacts if needed.

---

## License

Add your preferred license here (for example, MIT, Apache 2.0).
