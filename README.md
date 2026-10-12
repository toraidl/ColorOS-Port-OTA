# ColorOS-Port-OTA

Update metadata for the ColorOS / OxygenOS port project
(<https://github.com/toraidl/coloros_port>).

This repository holds **only data**: per-device update manifests and their
changelogs. The flashable packages themselves are **not** stored here, they
live on SourceForge:

<https://sourceforge.net/projects/coloros-port/files/>

The on-device updater (`com.oplus.ota`, patched to keep the official UI) reads
one JSON manifest per device at boot / manual check and renders it in the stock
"Software update" screen.

## Layout

```
devices/<DEVICE>.json        # source manifest, one per device (hand edited)
changelogs/<DEVICE>/<ver>.md # source changelog (Markdown)
dist/<DEVICE>.json           # generated - this is what the app fetches
dist/index.json              # generated device index
schema/device.schema.json    # JSON schema for devices/*.json
tools/validate.py            # schema + sanity checks (used by CI)
tools/build_dist.py          # renders changelogs and builds dist/
```

Never edit `dist/` by hand - it is regenerated from `devices/` + `changelogs/`.

## What the app fetches

The updater tries these URLs for `<DEVICE>` (its `ro.product.model`, upper
cased), in order, and stops at the first 2xx JSON response:

1. `persist.sys.portota.base` (override, for testing)
2. `https://cdn.jsdelivr.net/gh/toraidl/ColorOS-Port-OTA@main/dist/<DEVICE>.json`
3. `https://raw.githubusercontent.com/toraidl/ColorOS-Port-OTA/main/dist/<DEVICE>.json`

jsDelivr is preferred because it is a CDN mirror that stays reachable from
mainland China, where `raw.githubusercontent.com` is frequently blocked.

## Manifest fields

See `schema/device.schema.json`. The important ones:

| field | meaning |
|-------|---------|
| `device` | device code, must match `ro.product.model` (upper case) |
| `version` | new build id, e.g. `KB2000_17.0.0.152(CN01)` |
| `romVersion` / `coloros` / `android` | display values in the update card |
| `url` | direct package URL (SourceForge `/download` redirect works) |
| `size` / `md5` | optional integrity data, `0` / `""` when unknown |
| `id` | stable package id used for the local DB row |
| `changelog` | path to `changelogs/<DEVICE>/<ver>.md` |

`tools/build_dist.py` turns `changelog` into a rendered `description` (HTML)
so the app can show it without any network fetch of its own.

## Adding a release

1. Upload the package to SourceForge under `ColorOS17/<version>/`.
2. Bump `devices/<DEVICE>.json` (`version`, `url`, `id`, `size`, `md5`).
3. Add `changelogs/<DEVICE>/<version>.md`.
4. `python3 tools/validate.py && python3 tools/build_dist.py`
5. Commit `devices/`, `changelogs/` and `dist/`.

CI (`validate.yml`) re-runs steps 4 automatically and fails the build if the
manifest is invalid, so a broken entry can never reach a device.

## Version comparison

The updater compares numeric fields only: it strips everything up to the first
`_`, then reads the first four integers (`17.0.0.152` -> `[17, 0, 0, 152]`).
An update is offered only when the manifest version is strictly greater than
the running `ro.build.display.id`.
