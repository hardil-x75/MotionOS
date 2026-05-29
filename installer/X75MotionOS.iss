#define MyAppName "X75 MotionOS"
#define MyAppVersion "0.1.0-beta"
#define MyAppPublisher "X75 Labs"
#define MyAppURL "https://github.com/hardil-x75/MotionOS"
#define MyAppExeName "X75MotionOS.exe"
#define MyAppId "{{8F8BD9FB-0788-4DA1-86DE-916839CF8752}"

[Setup]
AppId={#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={localappdata}\Programs\X75 MotionOS
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE.md
OutputDir=..\release\installer
OutputBaseFilename=X75MotionOSSetup-0.1.0-beta
SetupIconFile=..\src\hands_free_control\assets\app-icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
VersionInfoVersion=0.1.0.0
VersionInfoCompany=X75 Labs
VersionInfoDescription=X75 MotionOS Installer
VersionInfoProductName=X75 MotionOS
VersionInfoProductVersion=0.1.0.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\X75MotionOS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\README.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\LICENSE.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\COPYRIGHT.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\SUPPORT.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\PRIVACY_POLICY.txt"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\TESTER_NOTES.md"; DestDir: "{app}\docs"; Flags: ignoreversion
Source: "..\docs\THIRD_PARTY_NOTICES.md"; DestDir: "{app}\docs"; Flags: ignoreversion

[Icons]
Name: "{group}\X75 MotionOS"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall X75 MotionOS"; Filename: "{uninstallexe}"
Name: "{autodesktop}\X75 MotionOS"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch X75 MotionOS"; Flags: nowait postinstall skipifsilent
