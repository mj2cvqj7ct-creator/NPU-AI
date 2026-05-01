; NPU Audio Enhancer - Inno Setup Installer Script
; Requires Inno Setup 6.2+ (https://jrsoftware.org/isinfo.php)

#define MyAppName "NPU Audio Enhancer"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "NPU-AI"
#define MyAppURL "https://github.com/mj2cvqj7ct-creator/NPU-AI"
#define MyAppExeName "NPU_Audio_Enhancer.exe"

[Setup]
AppId={{B8F3A2E1-7C4D-4E9A-B5F6-1A2D3C4E5F67}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Output installer to installer/output/
OutputDir=output
OutputBaseFilename=NPU_Audio_Enhancer_Setup_{#MyAppVersion}
; Use app icon
SetupIconFile=..\resources\icons\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
; Compression
Compression=lzma2/ultra64
SolidCompression=yes
; Require admin for Program Files install, but allow per-user
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; Modern wizard style
WizardStyle=modern
WizardSizePercent=120
; Architecture
ArchitecturesAllowed=arm64 x64
ArchitecturesInstallIn64BitMode=arm64 x64
; Appearance
WindowVisible=no
DisableWelcomePage=no
LicenseFile=..\LICENSE
; Minimum Windows version (Windows 11)
MinVersion=10.0.22000

[Languages]
Name: "japanese"; MessagesFile: "compiler:Languages\Japanese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checked
Name: "startupicon"; Description: "Windows起動時に自動実行"; GroupDescription: "追加オプション:"
Name: "addtopath"; Description: "PATHに追加"; GroupDescription: "追加オプション:"

[Files]
; Main application files from PyInstaller dist
Source: "..\dist\NPU_Audio_Enhancer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Icon
Source: "..\resources\icons\app.ico"; DestDir: "{app}\resources\icons"; Flags: ignoreversion
; License and README
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start menu
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\resources\icons\app.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{group}\README"; Filename: "{app}\README.md"
; Desktop
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\resources\icons\app.ico"; Tasks: desktopicon
; Startup
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--minimized"; Tasks: startupicon

[Registry]
; Add to PATH (optional)
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Tasks: addtopath; Check: NeedsAddPath(ExpandConstant('{app}'))
; File association for future use
Root: HKCU; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"
Root: HKCU; Subkey: "Software\{#MyAppPublisher}\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"

[Run]
; Launch after install
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Clean up app data
Type: filesandordirs; Name: "{localappdata}\{#MyAppName}"
Type: filesandordirs; Name: "{app}\data"
Type: filesandordirs; Name: "{app}\models"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\__pycache__"

[Code]
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER,
    'Environment', 'Path', OrigPath) then
  begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  OrigPath: string;
  NewPath: string;
  AppDir: string;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    AppDir := ExpandConstant('{app}');
    if RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath) then
    begin
      NewPath := OrigPath;
      StringChangeEx(NewPath, ';' + AppDir, '', True);
      StringChangeEx(NewPath, AppDir + ';', '', True);
      StringChangeEx(NewPath, AppDir, '', True);
      if NewPath <> OrigPath then
        RegWriteExpandStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', NewPath);
    end;
  end;
end;
