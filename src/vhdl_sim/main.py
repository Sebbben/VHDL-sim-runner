import argparse
import json
import os
import signal
import subprocess
import sys
from pathlib import Path

from .scanner import scan, Entity, Architecture
from .ui import prompt
from .generator import generate, MAKEFILE_NAME

LAST_RUN_FILE = "sim/.last_run.json"


def save_selection(root: Path, selection):
    data = {
        "entity":       selection.entity.name,
        "architecture": selection.architecture.name,
        "testbench":    str(selection.testbench.resolve()),
    }
    (root / LAST_RUN_FILE).write_text(json.dumps(data, indent=2))


def load_selection(root: Path, scan_result):
    last_run = root / LAST_RUN_FILE
    if not last_run.exists():
        print("Error: no previous run found. Run vhdl-sim without --rerun first.")
        sys.exit(1)

    data = json.loads(last_run.read_text())

    # look up the entity and architecture from the scan result
    entity = next(
        (e for e in scan_result.entities if e.name == data["entity"]),
        None
    )
    if entity is None:
        print(f"Error: previously used entity '{data['entity']}' no longer found in src/")
        sys.exit(1)

    architecture = next(
        (a for a in entity.architectures if a.name == data["architecture"]),
        None
    )
    if architecture is None:
        print(f"Error: previously used architecture '{data['architecture']}' no longer found.")
        sys.exit(1)

    testbench = Path(data["testbench"])
    if not testbench.exists():
        print(f"Error: previously used testbench '{testbench.name}' no longer found.")
        sys.exit(1)

    from .ui import SimSelection
    return SimSelection(entity=entity, architecture=architecture, testbench=testbench)


def run_simulation(makefile: Path):
    process = subprocess.Popen(
        ["make", "-f", MAKEFILE_NAME],
        cwd=makefile.parent,
        start_new_session=True,
    )
    try:
        process.wait()
    except KeyboardInterrupt:
        print("\nStopping simulation...")
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        print("Simulation stopped.")
        sys.exit(0)
    return process.returncode


def main():
    parser = argparse.ArgumentParser(description="VHDL simulation runner")
    parser.add_argument(
        "--rerun", action="store_true",
        help="re-run the last simulation without prompting"
    )
    args = parser.parse_args()

    root = Path.cwd()

    print("Scanning project...")
    try:
        result = scan(root)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)

    if args.rerun:
        selection = load_selection(root, result)
        print(f"Re-running: {selection.entity.name} / {selection.architecture.name} / {selection.testbench.name}")
    else:
        selection = prompt(result)

    save_selection(root, selection)
    makefile = generate(root, result, selection)

    if not args.rerun:
        print(f"\nGenerated {makefile}")

    print("Running simulation... (Ctrl+C to stop)\n")
    sys.exit(run_simulation(makefile))