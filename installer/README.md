# Windows installer

The installer uses Inno Setup 6 (ISCC.exe). It installs for the current Windows
user at `%LOCALAPPDATA%\Programs\AutoE7`, creates a Start Menu shortcut and
optionally a Desktop shortcut. It keeps the same AppId for upgrades and leaves
personal settings in `%LOCALAPPDATA%\AutoE7` when uninstalled.

Build only when requested, after building and checking the current application
payload. From the project root:

```powershell
./installer/build.ps1 -SourceDir ./dist/<build-folder>/AutoE7
```

Use `-CompilerPath` for a compiler outside the standard install directories,
`-OutputDir` to choose the artifact folder, or `-Version` for an explicitly
prepared local test version. Installer and payload versions must match.
Logs go in `build/installer-<version>/build.log`. This script neither builds
the application nor uploads, commits or publishes anything.

The installer adds `installation.json` beside the EXE. Portable builds do not
contain this marker. Installed app processes hold the mutex `AutoE7.Installed`.
Setup and Uninstall refuse to replace or remove a running installed app;
they never force-stop automation.

For an in-app upgrade, download and verify the complete installer first. Stop
automation, save settings, hand off to the internal `--apply-update` helper and exit the application.
The helper holds no app mutex and exits immediately after spawning Setup,
so it cannot keep the installed executable locked during replacement. The helper waits for the process to exit
before running:

```text
AutoE7-Setup-<version>.exe /VERYSILENT /SUPPRESSMSGBOXES /NORESTART /AUTORESTART=1 /DIR="<existing install directory>"
```

`/AUTORESTART=1` reopens AutoE7 after a successful silent installation. Omit it
when validating an installation without launching the UI. Interactive installs
show a normal final-page launch checkbox. Upgrade uses the existing directory
and uninstall registration. User settings are separate from installed files;
the installer does not delete or reset them.

After the installed app opens successfully, a background task deletes cached
Setup files for its own version and older versions from
`%LOCALAPPDATA%\AutoE7\updates\download-*`. It retries for up to a minute while
Setup releases the file. Newer installers (including failed upgrades), unrelated
files and manually downloaded installers outside this cache are retained.

Before publishing, test first install, upgrade, retained preferences, shortcuts,
the mutex guard, and uninstall. Local installers are not published releases.
