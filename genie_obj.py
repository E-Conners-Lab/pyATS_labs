"""
Collect OSPF operational state (Genie Ops) from one or more devices and save as JSON.

Usage examples (from your project root):
  python genie_obj_multi.py
    -> runs on ALL devices found in testbeds/testbed.yaml

  python genie_obj_multi.py --devices R1 R2 R3 R4
    -> runs only on the devices listed

  python genie_obj_multi.py --output-dir outputs/ospf_ops --log-stdout
"""

from genie import testbed as genie_testbed
from genie.libs.ops.ospf.iosxe.ospf import Ospf
from pathlib import Path
from datetime import datetime
import argparse
import json


def collect_ospf(tb, device_name: str, out_dir: Path, log_stdout: bool = False) -> Path:
    """Connect to a device, learn OSPF state, write JSON, disconnect, and return output path."""
    uut = tb.devices[device_name]

    # Avoid running any default init exec/config commands unless you want them.
    uut.connect(
        log_stdout=log_stdout,
        init_exec_commands=[],
        init_config_commands=[],
    )

    try:
        ospf_obj = Ospf(device=uut)
        ospf_obj.learn()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_file = out_dir / f"{device_name.lower()}_ospf_ops_{timestamp}.json"
        out_file.parent.mkdir(parents=True, exist_ok=True)

        with out_file.open("w", encoding="utf-8") as f:
            json.dump(ospf_obj.info, f, indent=2)

        return out_file
    finally:
        # Always disconnect even if learn() throws an exception
        try:
            uut.disconnect()
        except Exception:
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--testbed", default="testbeds/testbed.yaml", help="Path to Genie testbed YAML")
    parser.add_argument("--devices", nargs="*", help="Device names (keys) from testbed.yaml. If omitted, runs all.")
    parser.add_argument("--output-dir", default="outputs/ospf_ops", help="Directory for JSON outputs")
    parser.add_argument("--log-stdout", action="store_true", help="Show device I/O on stdout")
    args = parser.parse_args()

    tb = genie_testbed.load(args.testbed)
    out_dir = Path(args.output_dir)

    # If no devices specified, use all devices defined in the testbed
    target_devices = args.devices if args.devices else list(tb.devices.keys())

    print(f"Testbed: {args.testbed}")
    print(f"Targets: {', '.join(target_devices)}")
    print(f"Output:  {out_dir}\n")

    results = {}
    for name in target_devices:
        print(f"=== {name} ===")
        try:
            out_path = collect_ospf(tb, name, out_dir, log_stdout=args.log_stdout)
            results[name] = {"status": "ok", "file": str(out_path)}
            print(f"Saved: {out_path}\n")
        except Exception as e:
            results[name] = {"status": "error", "error": repr(e)}
            print(f"ERROR on {name}: {e}\n")

    # Write a run summary
    summary = out_dir / "run_summary.json"
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Run summary: {summary}")


if __name__ == "__main__":
    main()
