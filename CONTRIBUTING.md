# Contributing

Thanks for helping! This project is small and friendly.

## Dev setup

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev,video]"
ZVSTUDIO_BACKEND=mock zvstudio daemon   # http://127.0.0.1:8787, no hardware needed
pytest
ruff check .
```

The **mock** backend means you can build and test everything without an ASUS panel —
the web UI mirrors exactly what would be on screen.

## Adding an applet

1. Subclass `zvstudio.core.applets.base.Applet`, set `meta`, implement `render(ctx)`.
2. Either drop it in `zvstudio/core/applets/` and add it to
   `zvstudio/core/registry.py:BUILTIN`, or ship it in your own package with a
   `zvstudio.applets` entry point (see `examples/`).
3. Keep `render()` cheap — it runs every frame. Use `self.config` for options and
   declare them in `meta.config_schema` so the UI can expose them.

## Supporting another panel

Implement a `Panel` backend (`zvstudio/core/device/base.py`) — `show_image`,
`begin_stream`, `push_frame`, `set_brightness` — and wire it into
`zvstudio/core/device/__init__.py:get_panel`. If you have a different ASUS lid OLED,
please open an issue with `lsusb` + your model.

## Style

`ruff` for lint/format, type hints welcome, keep it dependency-light.
