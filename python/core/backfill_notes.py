import json
from pathlib import Path

DEFAULT_NOTES_BY_MODE = {
    "rl": "rl test",
    "pid": "pid control",
    "manual": "manual control",
    "sysid": "sysid test",
}

# Placeholder values that count as "not actually a note" alongside null
BLANK_VALUES = {None, "", "0"}

ARCHIVE_PREFIXES = ("divesync-heavy-v",)


def backfill(data_dir="data", dry_run=False):
    data_path = Path(data_dir)
    updated, skipped_no_meta, already_set = [], [], []

    for folder in sorted(data_path.iterdir()):
        if not folder.is_dir() or folder.name.startswith(ARCHIVE_PREFIXES):
            continue

        meta_path = folder / "metadata.json"
        if not meta_path.exists():
            skipped_no_meta.append(folder.name)
            continue

        meta = json.loads(meta_path.read_text())
        if meta.get("notes") not in BLANK_VALUES:
            already_set.append(folder.name)
            continue

        mode = meta.get("control-mode", "")
        new_notes = DEFAULT_NOTES_BY_MODE.get(mode, f"{mode} test" if mode else "test")
        meta["notes"] = new_notes
        updated.append((folder.name, new_notes))

        if not dry_run:
            meta_path.write_text(json.dumps(meta, indent=4))

    print(f"Updated: {len(updated)}")
    for name, notes in updated:
        print(f"  {name} -> {notes!r}")
    print(f"Already had notes, left alone: {len(already_set)}")
    print(f"No metadata.json, skipped: {skipped_no_meta}")


if __name__ == "__main__":
    backfill()
