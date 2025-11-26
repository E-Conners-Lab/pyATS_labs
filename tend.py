#!/usr/bin/env python3
"""
OSPF Flap Test Trend Analyzer

Tracks OSPF convergence performance over time across multiple test runs.
Useful for identifying degradation, improvements, and establishing baselines.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict


def find_all_result_files(results_dir):
    """Find all OSPF flap result JSON files in results directory"""
    results_path = Path(results_dir)
    if not results_path.exists():
        return []

    json_files = list(results_path.glob("ospf_flap_*/ospf_flap_results.json"))
    return sorted(json_files)


def load_all_results(json_files):
    """Load all test results from multiple files"""
    all_results = []

    for json_file in json_files:
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                # Extract timestamp from directory name
                timestamp_str = json_file.parent.name.replace('ospf_flap_', '')

                for result in data:
                    result['test_run'] = timestamp_str
                    all_results.append(result)
        except Exception as e:
            print(f"Warning: Could not load {json_file}: {e}")

    return all_results


def analyze_convergence_trends(results):
    """Analyze convergence time trends"""
    # Group by interface
    by_interface = defaultdict(list)

    for result in results:
        key = f"{result['device']}-{result['interface']}"
        if 'convergence_time' in result:
            by_interface[key].append({
                'timestamp': result['test_run'],
                'time': result['convergence_time'],
                'status': result['status']
            })

    trends = {}
    for interface, measurements in by_interface.items():
        if len(measurements) < 2:
            continue

        times = [m['time'] for m in measurements]
        avg = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        # Calculate trend (improving/degrading)
        first_half = sum(times[:len(times) // 2]) / (len(times) // 2)
        second_half = sum(times[len(times) // 2:]) / (len(times) - len(times) // 2)
        trend = "IMPROVING" if second_half < first_half else "DEGRADING" if second_half > first_half else "STABLE"

        trends[interface] = {
            'measurements': len(measurements),
            'average': avg,
            'min': min_time,
            'max': max_time,
            'first_half_avg': first_half,
            'second_half_avg': second_half,
            'trend': trend,
            'data': measurements
        }

    return trends


def analyze_stability(results):
    """Analyze OSPF stability (DR/BDR changes, failures)"""
    stability_metrics = {
        'total_tests': len(results),
        'passed': 0,
        'partial': 0,
        'failed': 0,
        'dr_bdr_changes': 0,
        'avg_convergence': 0
    }

    convergence_times = []

    for result in results:
        if result['status'] == 'PASSED':
            stability_metrics['passed'] += 1
        elif result['status'] == 'PARTIAL':
            stability_metrics['partial'] += 1
        else:
            stability_metrics['failed'] += 1

        if 'convergence_time' in result:
            convergence_times.append(result['convergence_time'])

        # Check for DR/BDR changes
        if 'baseline_neighbors' in result and 'final_neighbors' in result:
            for neighbor in result['baseline_neighbors']:
                if neighbor in result['final_neighbors']:
                    baseline_state = result['baseline_neighbors'][neighbor]['state']
                    final_state = result['final_neighbors'][neighbor]['state']
                    if baseline_state != final_state:
                        stability_metrics['dr_bdr_changes'] += 1

    if convergence_times:
        stability_metrics['avg_convergence'] = sum(convergence_times) / len(convergence_times)

    return stability_metrics


def generate_trend_report(trends, stability):
    """Generate comprehensive trend report"""
    report = []
    report.append("=" * 80)
    report.append("OSPF FLAP TEST - TREND ANALYSIS REPORT")
    report.append("=" * 80)
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")

    # Overall Stability
    report.append("OVERALL STABILITY")
    report.append("-" * 80)
    report.append(f"Total Test Runs:    {stability['total_tests']}")
    report.append(
        f"Passed:             {stability['passed']} ({stability['passed'] / stability['total_tests'] * 100:.1f}%)")
    report.append(
        f"Partial:            {stability['partial']} ({stability['partial'] / stability['total_tests'] * 100:.1f}%)")
    report.append(
        f"Failed:             {stability['failed']} ({stability['failed'] / stability['total_tests'] * 100:.1f}%)")
    report.append(f"DR/BDR Changes:     {stability['dr_bdr_changes']}")
    report.append(f"Avg Convergence:    {stability['avg_convergence']:.2f} seconds")
    report.append("")

    # Interface-by-Interface Trends
    report.append("CONVERGENCE TRENDS BY INTERFACE")
    report.append("-" * 80)

    for interface, trend_data in sorted(trends.items()):
        report.append(f"\n{interface}")
        report.append(f"  Measurements:     {trend_data['measurements']}")
        report.append(f"  Average:          {trend_data['average']:.2f} seconds")
        report.append(f"  Min:              {trend_data['min']:.2f} seconds")
        report.append(f"  Max:              {trend_data['max']:.2f} seconds")
        report.append(f"  Trend:            {trend_data['trend']}")

        if trend_data['trend'] == 'IMPROVING':
            improvement = ((trend_data['first_half_avg'] - trend_data['second_half_avg']) /
                           trend_data['first_half_avg'] * 100)
            report.append(f"  Improvement:      {improvement:.1f}%")
        elif trend_data['trend'] == 'DEGRADING':
            degradation = ((trend_data['second_half_avg'] - trend_data['first_half_avg']) /
                           trend_data['first_half_avg'] * 100)
            report.append(f"  Degradation:      {degradation:.1f}%")

    report.append("")

    # Recommendations
    report.append("TREND-BASED RECOMMENDATIONS")
    report.append("-" * 80)

    degrading_interfaces = [i for i, t in trends.items() if t['trend'] == 'DEGRADING']
    if degrading_interfaces:
        report.append("\n⚠️  WARNING: Performance degradation detected")
        for interface in degrading_interfaces:
            report.append(f"   - {interface}")
        report.append("   Action: Investigate network changes, traffic patterns, or hardware issues")

    if stability['dr_bdr_changes'] > len(stability) * 0.3:
        report.append("\n⚠️  WARNING: High DR/BDR role instability")
        report.append("   Action: Consider setting OSPF priorities to stabilize roles")

    if stability['avg_convergence'] > 10:
        report.append("\n⚠️  WARNING: Convergence time exceeds 10 seconds")
        report.append("   Action: Tune OSPF timers (hello, dead intervals)")

    if not degrading_interfaces and stability['failed'] == 0:
        report.append("\n✅ Network performance is stable with no degradation")

    report.append("")
    report.append("=" * 80)

    return "\n".join(report)


def generate_html_trend_chart(trends):
    """Generate HTML with trend visualization"""
    html = """<!DOCTYPE html>
<html>
<head>
    <title>OSPF Convergence Trends</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 50px auto;
            padding: 20px;
            background: #f5f5f5;
        }
        .chart-container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        h1 {
            color: #2c3e50;
            text-align: center;
        }
    </style>
</head>
<body>
    <h1>📈 OSPF Convergence Trends Over Time</h1>
"""

    for interface, trend_data in trends.items():
        timestamps = [m['timestamp'] for m in trend_data['data']]
        times = [m['time'] for m in trend_data['data']]

        html += f"""
    <div class="chart-container">
        <canvas id="chart_{interface.replace('-', '_')}"></canvas>
    </div>
    <script>
        new Chart(document.getElementById('chart_{interface.replace('-', '_')}'), {{
            type: 'line',
            data: {{
                labels: {timestamps},
                datasets: [{{
                    label: '{interface}',
                    data: {times},
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1,
                    fill: false
                }}]
            }},
            options: {{
                responsive: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Convergence Time: {interface}'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Convergence Time (seconds)'
                        }}
                    }}
                }}
            }}
        }});
    </script>
"""

    html += """
</body>
</html>
"""
    return html


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python ospf_trend_analysis.py <results_directory>")
        print("\nExample:")
        print("  python ospf_trend_analysis.py results/")
        sys.exit(1)

    results_dir = sys.argv[1]

    # Find all result files
    json_files = find_all_result_files(results_dir)

    if not json_files:
        print(f"No test result files found in {results_dir}")
        sys.exit(1)

    print(f"Found {len(json_files)} test result files")

    # Load all results
    all_results = load_all_results(json_files)
    print(f"Loaded {len(all_results)} individual test results")

    # Analyze trends
    trends = analyze_convergence_trends(all_results)
    stability = analyze_stability(all_results)

    # Generate report
    report = generate_trend_report(trends, stability)
    print("\n" + report)

    # Save outputs
    output_dir = Path(results_dir)

    # Save text report
    report_file = output_dir / "trend_analysis.txt"
    with open(report_file, 'w') as f:
        f.write(report)
    print(f"\n📄 Trend report saved: {report_file}")

    # Generate HTML chart
    if trends:
        html_chart = generate_html_trend_chart(trends)
        chart_file = output_dir / "trend_chart.html"
        with open(chart_file, 'w') as f:
            f.write(html_chart)
        print(f"📊 Trend chart saved: {chart_file}")

    print("\n✅ Trend analysis complete!")


if __name__ == "__main__":
    main()