# Building FM Tactics Lab

## Requirements

- Windows x64, full CPython 3.12 x64, MSVC C++17, the Windows SDK, Rust MSVC toolchain and WebView2.
- A local FM27 installation. The [Steam reference](../native/adapter_version.json) and [current Epic reference](../native/epic_27_1_adapter_version.json) both use build `27.1.0+2505117` with storefront-specific compatibility checks. The [previous Epic build](../native/epic_adapter_version.json) uses its own reference DLL for FM27 `27.0.1`.
- A verified v1108.5 EXE from this repository's Releases, used to supply the matching initial inputs.

Install the save reader and its compression dependency from requirements.txt in the build environment.

## Prepare local inputs

Run these commands from the repository root:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe scripts/prepare_private.py --release-exe "D:\Downloads\FM27-Tactics-Lab-v1108.5.exe"
```

The script checks the original EXE and embedded payload SHA256, then reads only the named input assets into ignored `private/` directories. It does not execute the EXE. An existing matching asset directory can alternatively be supplied with `--assets-root` and `--catalog`.

## Build the native adapter

In an **x64 Native Tools Command Prompt for Visual Studio**:

```bat
.venv\Scripts\python.exe scripts\build_native.py --reference-dll "D:\Games\Football Manager 27\fm_Data\Plugins\x86_64\game_plugin.dll"
```

The public repository contains range metadata and digests. The script reconstructs comparison bytes from the exact reference DLL on your machine, verifies every range, then compiles the checked-in C++ host. Generated function bytes remain in ignored local outputs.

Use `--platform epic_27_1` for the current Epic DLL and `--platform epic` for the prior Epic DLL. The same option selects the adapter when using `scripts/run.py`.

Generate the Steam 27.1 personal instruction rules for the local catalog before running or packaging the desktop app.

```powershell
$env:FM27_GAME_ROOT = "D:\Games\Football Manager 27"
$env:FM27_ENGINE_ROOT = (Resolve-Path private/engine).Path
.\private\engine\fm27_native\FM27Simulator.exe --policy-audit --output build/steam-policies.jsonl
.venv\Scripts\python.exe scripts/update_steam_policy.py build/steam-policies.jsonl
```

## Run from source

```powershell
.venv\Scripts\python.exe scripts/run.py --game-root "D:\Games\Football Manager 27"
```

Open the printed loopback URL to run the development server. Press `Ctrl+C` to stop it. The packaged Tauri app uses pipes for backend requests.

## Build a local desktop EXE

```powershell
.venv\Scripts\python.exe scripts/build_exe.py --python-home "D:\Python312"
```

Supply a full CPython 3.12 x64 distribution containing `Lib`, `DLLs`, `python312.dll`, the runtime libraries and `LICENSE.txt`. Prepare the three adapters with their matching game DLLs. The Tauri build outputs a single EXE in `dist/` with the Steam and Epic adapters. Use `--output` to choose a different path for a local build.

The build script packages the save reader from the active Python environment. The release EXE and a local build can have different hashes.

## Validate and export source

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
.venv\Scripts\python.exe scripts/export_source.py
```

The exporter uses the `PUBLIC_DOCS` list in [scripts/export_source.py](../scripts/export_source.py) to select individual Markdown files. Keep maintainer materials in local storage. The archive includes file digests and checks for workstation paths, common credential formats and generated comparison bytes.

The EXE release is a separate asset authorized for distribution by the maintainer. Its embedded initial inputs and comparison data are outside the MIT grant for tool code. See [third-party notices](../THIRD_PARTY_NOTICES.md).
