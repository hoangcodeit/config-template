from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import DoubleQuotedScalarString


def make_yaml() -> YAML:
    y = YAML()
    y.preserve_quotes = True
    y.default_flow_style = False
    y.width = 120
    y.indent(mapping=2, sequence=4, offset=2)
    return y


def load_template(filename: str, templates_dir: Path) -> CommentedMap:
    y = make_yaml()
    with open(templates_dir / filename, encoding="utf-8") as fh:
        return y.load(fh)


def save_yaml(data: CommentedMap, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    y = make_yaml()
    with open(path, "w", encoding="utf-8") as fh:
        y.dump(data, fh)


def make_flow_list(items: list) -> CommentedSeq:
    """Return a ruamel.yaml sequence that serialises as ``["a", "b"]`` (flow style, quoted)."""
    seq = CommentedSeq([DoubleQuotedScalarString(i) for i in items])
    seq.fa.set_flow_style()
    return seq


def make_column_entry(
    name: str,
    dtype: str,
    nullable: bool = True,
    description: str = "",
) -> CommentedMap:
    entry = CommentedMap()
    entry["name"]        = name
    entry["type"]        = dtype
    entry["nullable"]    = nullable
    entry["description"] = description
    return entry
