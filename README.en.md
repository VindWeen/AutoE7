# AutoE7

[Tiếng Việt](README.md) | [English](README.en.md)

A Windows automation tool for Epic Seven, powered by image recognition, with Vietnamese and English interfaces.

## Features

- **Episode** — repeat the selected stage and handle story skips and result screens.
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

Open **Settings** in the top-right corner to change the language or check for updates. When a newer version is available, you can choose to open its download page.

Options for each activity are saved automatically to `%LOCALAPPDATA%\AutoE7\settings.json` and restored when switching activities or reopening the app. AutoE7 remembers the last activity and waits for you to click **Start**.

## Notes

- Reference images currently use the game's English interface. UI changes and visual effects may affect recognition.
- Background clicks and covered-window capture are experimental. Keep the game window restored while running.
- Hunt is not supported yet. Try a single run before starting a longer session.

[Portable guide (Vietnamese/English)](PORTABLE-GUIDE.txt) · [Tests](tests/README.md) · [Release process (Vietnamese)](RELEASING.md) · [Report an issue](https://github.com/VindWeen/AutoE7/issues)
