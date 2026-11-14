; Compile through build.ps1 so paths and version are passed explicitly.
#ifndef SourceDir
  #error SourceDir is required
#endif
#ifndef OutputDir
  #error OutputDir is required
#endif
#ifndef AppVersion
  #error AppVersion is required
#endif
#ifndef AppFileVersion
  #error AppFileVersion is required
#endif

[Setup]
AppId={{91627F4D-BCF8-4535-BD25-0CB455E35396}
AppName=AutoE7
AppVersion={#AppVersion}
VersionInfoVersion={#AppFileVersion}
AppPublisher=VindWeen
AppPublisherURL=https://github.com/VindWeen/AutoE7
AppSupportURL=https://github.com/VindWeen/AutoE7/issues
DefaultDirName={localappdata}\Programs\AutoE7
DefaultGroupName=AutoE7
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#OutputDir}
OutputBaseFilename=AutoE7-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\assets\branding\app.ico
UninstallDisplayIcon={app}\AutoE7.exe
AppMutex=AutoE7.Installed
CloseApplications=no
RestartApplications=no
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "installation.json"
Source: "installation.json"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\AutoE7"; Filename: "{app}\AutoE7.exe"; WorkingDir: "{app}"; IconFilename: "{app}\assets\branding\app.ico"; IconIndex: 0; AppUserModelID: "VindWeen.AutoE7"
Name: "{autodesktop}\AutoE7"; Filename: "{app}\AutoE7.exe"; WorkingDir: "{app}"; IconFilename: "{app}\assets\branding\app.ico"; IconIndex: 0; AppUserModelID: "VindWeen.AutoE7"; Tasks: desktopicon

[Run]
Filename: "{app}\AutoE7.exe"; WorkingDir: "{app}"; Description: "Open AutoE7"; Flags: nowait postinstall skipifsilent
Filename: "{app}\AutoE7.exe"; WorkingDir: "{app}"; Flags: nowait; Check: ShouldRestartAfterUpdate

[Code]
function ShouldRestartAfterUpdate: Boolean;
begin
  Result := WizardSilent and (ExpandConstant('{param:AUTORESTART|0}') = '1');
end;
