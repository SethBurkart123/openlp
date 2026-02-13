# OpenLP Packaging

This directory contains the OpenLP packaging builders synchronized from `https://gitlab.com/openlp/packaging` `master`.

## Quick build recipes (PyQt5)

```bash
cd ./packaging/builders
uv run macos-builder.py --config ../macos/config.ini --skip-update --use-qt5
uv run windows-builder.py --config ../windows/config.ini --skip-update --use-qt5
uv run flatpak-builder.py 3.1.7 --project <gitlab_project_id> --token <token>
```

- Use `--use-qt5` for this branch (PyQt5-based OpenLP source tree).
- Use `--skip-update` to avoid branch updates when building from an already-prepared workspace.

`packaging/windows/config.ini` and `packaging/macos/config.ini` should point at the correct local checkout path for your environment.
