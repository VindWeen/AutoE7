# AutoE7

[Tiếng Việt](README.md) | [English](README.en.md)

A Windows automation tool for Epic Seven, powered by image recognition, with Vietnamese and English interfaces.

## Features

- **Episode** — enter from the lobby or recognize the current stage to resume; repeat the selected stage and handle skips and results.
- **Abyss** — run a set number of floors, advance between floors, and use Guardians.
- **Rookie Arena** — select opponents, track wins and losses, and manage battle flags.
- **Secret Shop** — refresh and buy selected items within a Skystone budget.
- Detection-only mode, clicks that keep your mouse free, and covered-window capture.
- Update checks through GitHub Releases; press **F8** to stop automation.

## Getting started

### Run from source

Requires **Windows 10/11**, **Python 3.11+**, Tkinter, and the Python Launcher (`py`).

Download or clone this repository, then open **`run.bat`**. The script installs the required dependencies and starts the application.

Alternatively, run these commands from the project directory:

```powershell
py -m pip install -r requirements.txt
py app.py
```

### Portable version

Download the ZIP from [GitHub Releases](https://github.com/VindWeen/AutoE7/releases), extract the entire archive, and open **`AutoE7.exe`**. The portable version does not require a Python installation.

## Usage

1. Open the game, prepare your team, and navigate to the starting screen for your chosen activity.
2. Select the game window, activity, and limits in AutoE7.
3. Try **Detection only** first, then turn it off to allow clicks.
4. Click **Start**. Use **Stop** or **F8** to end the session.

On startup, AutoE7 checks once in the background and shows the result beside its title. Click an available-update notice to view details and open the download page. Offline use remains available. Open **Settings** to change the language, toggle automatic checks, or check manually.

Options for each activity are saved automatically to `%LOCALAPPDATA%\AutoE7\settings.json` and restored when switching activities or reopening the app. AutoE7 remembers the last activity and waits for you to click **Start**.

Episode supports the idle or visible-menu lobby, Ready, team selection, ongoing stages, and known result screens. Each Start begins a new run count; an unfinished stage counts when it completes and returns to Ready. Unknown screens cause the tool to wait without guessing clicks.

Secret Shop, Rookie Arena, and Abyss can also start from the lobby or resume at supported screens. Abyss selects Normal, swipes the Battle list to the right, and enters normal Abyss. Prepare your team and battle settings beforehand. Each Start uses a fresh limit/budget; existing purchase or Refresh dialogs are closed and reevaluated without guessing prior spending.

## Notes

- Reference images currently use the game's English interface. UI changes and visual effects may affect recognition.
- Background clicks and covered-window capture are experimental. Keep the game window restored while running.
- Hunt is not supported yet. Try a single run before starting a longer session.

[Portable guide (Vietnamese/English)](PORTABLE-GUIDE.txt) · [Tests](tests/README.md) · [Release process (Vietnamese)](RELEASING.md) · [Report an issue](https://github.com/VindWeen/AutoE7/issues)
