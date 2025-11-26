# ospf_flap_job_advanced.py
"""
Advanced PyATS Job File for OSPF Interface Flap Testing

This job file allows you to:
- Test multiple devices and interfaces
- Customize timing parameters
- Export results to JSON

Usage:
    # Basic run
    pyats run job ospf_flap_job_advanced.py --testbed-file testbeds/testbed.yaml

    # With custom parameters
    pyats run job ospf_flap_job_advanced.py --testbed-file testbeds/testbed.yaml \
        --test-device R2 --test-interface GigabitEthernet0/1
"""

from pyats.easypy import run
import argparse


def main(runtime):
    """
    Main job entry point with customizable parameters
    """

    # Parse custom arguments if provided
    custom_args = runtime.args

    # Define test configurations
    # Default: test both interfaces on R1
    test_configs = [
        {"device": "R1", "interface": "GigabitEthernet0/1"},
        {"device": "R1", "interface": "GigabitEthernet0/2"},
    ]

    # Override if specific device/interface provided via command line
    if hasattr(custom_args, 'test_device') and hasattr(custom_args, 'test_interface'):
        test_configs = [
            {"device": custom_args.test_device, "interface": custom_args.test_interface}
        ]

    # Timing parameters (can be customized)
    shutdown_wait = getattr(custom_args, 'shutdown_wait', 3)
    startup_wait = getattr(custom_args, 'startup_wait', 5)
    convergence_timeout = getattr(custom_args, 'convergence_timeout', 60)

    # Run the advanced test script with parameters
    run(
        testscript='ospf_flap_test_advanced.py',
        runtime=runtime,
        taskid='OSPF_Flap_Advanced',
        test_configs=test_configs,
        shutdown_wait=shutdown_wait,
        startup_wait=startup_wait,
        convergence_timeout=convergence_timeout,
        convergence_check_interval=5,
        export_results=True,
        results_dir='results'
    )


# Add custom argument parser for command-line options
def configure_parser(parser):
    """Configure parser with custom arguments"""
    parser.add_argument(
        '--test-device',
        type=str,
        help='Device to test (e.g., R1)'
    )
    parser.add_argument(
        '--test-interface',
        type=str,
        help='Interface to flap (e.g., GigabitEthernet0/1)'
    )
    parser.add_argument(
        '--shutdown-wait',
        type=int,
        default=3,
        help='Seconds to wait after shutdown (default: 3)'
    )
    parser.add_argument(
        '--startup-wait',
        type=int,
        default=5,
        help='Seconds to wait after startup (default: 5)'
    )
    parser.add_argument(
        '--convergence-timeout',
        type=int,
        default=60,
        help='Max seconds to wait for OSPF convergence (default: 60)'
    )

    return parser
