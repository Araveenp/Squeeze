[Setup]
AppName=Squeeze
AppVersion=1.0
AppPublisher=Araveen
DefaultDirName={autopf}\Squeeze
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=.
OutputBaseFilename=SqueezeSetup
SetupIconFile=squeeze.ico
UninstallDisplayIcon={app}\Squeeze.exe
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=force

[Tasks]
Name: "startup"; Description: "Start Squeeze when Windows starts"

[Files]
Source: "dist\Squeeze\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\Squeeze"; Filename: "{app}\Squeeze.exe"

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Squeeze"; ValueData: """{app}\Squeeze.exe"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\Squeeze.exe"; Description: "Start Squeeze now"; Flags: nowait postinstall skipifsilent
