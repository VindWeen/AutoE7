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

## Download and install

Choose a build from the [**latest release**](https://github.com/VindWeen/AutoE7/releases/latest). Both support **Windows 10/11 x64** and work without Python.

| Build | Getting started | Updates |
| --- | --- | --- |
| **Portable ZIP** | Extract everything and open `AutoE7.exe` | Download the new ZIP and extract into a new folder |
| **Setup EXE** | Run Setup, then launch from Start Menu or the optional Desktop shortcut | Click **Update** in the app |

Stop the old app before upgrading. Setup defaults to `%LOCALAPPDATA%\Programs\AutoE7`; uninstall through Windows Settings → Apps.

Installed builds download Setup, verify SHA-256, save preferences, close the app, upgrade in the existing directory, and reopen. After successful startup, cached installers for the current and older versions are removed. Offline use and download failures leave the current app usable.

### Run from source

Requires **Python 3.11+**, Tkinter, and the Python Launcher (`py`). Clone the repository and open **`run.bat`** to install dependencies and launch, or run:

```powershell
py -m pip install -r requirements.txt
py app.py
```

## Usage

1. Open the game, prepare your team, and navigate to the starting screen for your chosen activity.
2. Select the game window, activity, and limits in AutoE7.
3. Try **Detection only** first, then turn it off to allow clicks.
4. Click **Start**. Use **Stop** or **F8** to end the session.

When automatic checks are enabled, AutoE7 checks once in the background on startup and shows the result beside its title. Click a new-version notice for details: installed builds offer **Update**, while portable builds open the ZIP download page. Offline use remains available. Open **Settings** to change the language, toggle automatic checks, or check manually.

Options for each activity are saved automatically to `%LOCALAPPDATA%\AutoE7\settings.json` and restored when switching activities or reopening the app. AutoE7 remembers the last activity and waits for you to click **Start**. Preferences survive upgrades and uninstalling the installed app.

Episode supports the idle or visible-menu lobby, Ready, team selection, ongoing stages, and known result screens. Each Start begins a new run count; an unfinished stage counts when it completes and returns to Ready. Unknown screens cause the tool to wait without guessing clicks.

Secret Shop, Rookie Arena, and Abyss can also start from the lobby or resume at supported screens. Abyss selects Normal, swipes the Battle list to the right, and enters normal Abyss. Prepare your team and battle settings beforehand. Each Start uses a fresh limit/budget; existing purchase or Refresh dialogs are closed and reevaluated without guessing prior spending.

## Notes

- Reference images currently use the game's English interface. UI changes and visual effects may affect recognition.
- Background clicks and covered-window capture are experimental. Keep the game window restored while running.
- Hunt is not supported yet. Try a single run before starting a longer session.

[Installation guide](INSTALL-GUIDE.txt) · [Portable guide (Vietnamese/English)](PORTABLE-GUIDE.txt) · [Tests](tests/README.md) · [Release process (Vietnamese)](RELEASING.md) · [Report an issue](https://github.com/VindWeen/AutoE7/issues)
