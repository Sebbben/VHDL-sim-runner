import sys
import questionary
from pathlib import Path
from dataclasses import dataclass

from .scanner import ScanResult, Entity, Architecture


@dataclass
class SimSelection:
    entity: Entity
    architecture: Architecture
    testbench: Path


def _select_entity(scan: ScanResult) -> Entity:
    def entity_label(e: Entity) -> str:
        if not e.architectures:
            return f"{e.name}  [no architectures — cannot simulate]"
        arch_names = ', '.join(a.name for a in e.architectures)
        return f"{e.name}  [{arch_names}]"

    choices = [
        questionary.Choice(
            title=entity_label(e),
            value=e,
            disabled="no architectures found" if not e.architectures else None,
        )
        for e in scan.entities
    ]

    if not choices:
        print("Error: no VHDL entities found under src/")
        sys.exit(1)

    return questionary.select(
        "Select entity to simulate:",
        choices=choices,
    ).ask()


def _select_architecture(entity: Entity) -> Architecture:
    # single architecture — skip the prompt
    if len(entity.architectures) == 1:
        return entity.architectures[0]

    choices = [
        questionary.Choice(
            title=f"{a.name}  ({a.source_file.name})",
            value=a,
        )
        for a in entity.architectures
    ]

    return questionary.select(
        f"Multiple architectures found for '{entity.name}' — select one:",
        choices=choices,
    ).ask()


def _select_testbench(scan: ScanResult, entity: Entity) -> Path:
    expected_name = f"tb_{entity.name}.py"

    matched   = [tb for tb in scan.testbenches if tb.name.lower() == expected_name.lower()]
    unmatched = [tb for tb in scan.testbenches if tb.name.lower() != expected_name.lower()]

    choices = []

    if matched:
        choices += [
            questionary.Choice(title=f"{tb.name}  [matched]", value=tb)
            for tb in matched
        ]

    if unmatched:
        if matched:
            # visual separator between matched and unmatched
            choices.append(questionary.Separator("── other testbenches ──"))
        choices += [
            questionary.Choice(title=tb.name, value=tb)
            for tb in unmatched
        ]

    if not choices:
        print(f"Error: no testbenches found in test/")
        sys.exit(1)

    if not matched:
        print(
            f"Warning: no testbench named '{expected_name}' found.\n"
            f"You can continue with another testbench or exit."
        )
        choices.append(questionary.Separator("──────────────────────"))
        choices.append(questionary.Choice(title="Exit", value=None))

    result = questionary.select(
        f"Select testbench for '{entity.name}':",
        choices=choices,
    ).ask()

    if result is None:
        print("Exiting.")
        sys.exit(0)

    return result


def prompt(scan: ScanResult) -> SimSelection:
    entity       = _select_entity(scan)
    architecture = _select_architecture(entity)
    testbench    = _select_testbench(scan, entity)

    return SimSelection(
        entity=entity,
        architecture=architecture,
        testbench=testbench,
    )