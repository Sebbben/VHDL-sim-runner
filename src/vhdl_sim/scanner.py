import re
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class Architecture:
    name: str
    source_file: Path


@dataclass
class Entity:
    name: str
    source_file: Path
    architectures: list[Architecture] = field(default_factory=list)


@dataclass
class ScanResult:
    entities: list[Entity]
    testbenches: list[Path]
    source_dirs: list[Path]


ENTITY_RE = re.compile(r'^\s*entity\s+(\w+)\s+is', re.IGNORECASE | re.MULTILINE)
ARCH_RE   = re.compile(r'^\s*architecture\s+(\w+)\s+of\s+(\w+)\s+is', re.IGNORECASE | re.MULTILINE)


def scan(root: Path) -> ScanResult:
    src_dir  = root / 'src'
    test_dir = root / 'test'

    if not src_dir.is_dir():
        raise FileNotFoundError(f"No src/ directory found under {root}")

    vhd_files   = sorted(src_dir.rglob('*.vhd'))
    source_dirs = sorted({f.parent for f in vhd_files})

    # parse entities and architectures from all .vhd files
    entities: dict[str, Entity] = {}

    for vhd_file in vhd_files:
        text = vhd_file.read_text(encoding='utf-8', errors='ignore')

        for match in ENTITY_RE.finditer(text):
            name = match.group(1).lower()
            if name not in entities:
                entities[name] = Entity(name=name, source_file=vhd_file)

        for match in ARCH_RE.finditer(text):
            arch_name   = match.group(1).lower()
            entity_name = match.group(2).lower()
            if entity_name in entities:
                entities[entity_name].architectures.append(
                    Architecture(name=arch_name, source_file=vhd_file)
                )

    # find testbenches
    testbenches: list[Path] = []
    if test_dir.is_dir():
        testbenches = sorted(test_dir.glob('tb_*.py'))

    return ScanResult(
        entities=sorted(entities.values(), key=lambda e: e.name),
        testbenches=testbenches,
        source_dirs=source_dirs,
    )

if __name__ == '__main__':
    from pprint import pprint
    result = scan(Path.cwd())
    pprint(result)