# pyATS Connectivity Interface Check

This project is a small but complete **pyATS / Genie** lab that connects to a testbed, runs a basic health check, and writes the results to a report file. It’s meant as a starting point for building out more advanced network automation and testing workflows.

---

## Project Overview

The core test script:

- Loads a pyATS / Genie testbed.
- Connects to every device in the testbed.
- Parses `show ip interface brief` using Genie.
- Verifies that **GigabitEthernet0/0** has a configured IP address.
- Logs results and writes a summary to `interface_report.txt`. :contentReference[oaicite:0]{index=0}

The job file:

- Is an **easypy job** that runs the connectivity test script.
- Lets you point to any testbed file at runtime with `--testbed-file`. :contentReference[oaicite:1]{index=1}

---

## Repository Structure

```text
pyats_labs/
├── connectivity_test.py        # AEtest script: connects & checks interfaces
├── connectivity_test_job.py    # easypy job: runs the testscript
├── testbeds/
│   └── testbed.yaml            # pyATS testbed definition (your devices)
├── interface_report.txt        # Generated test report (output)
└── README.md                   # Project documentation
