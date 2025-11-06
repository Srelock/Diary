; ========================================
; Inno Setup Script for Diary App
; Building Management Diary Application
; ========================================

#define MyAppName "Building Management Diary"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Building Management"
#define MyAppURL "https://github.com/Srelock/Diary"
#define MyAppExeName "diary_app.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
AppId={{8F3A2B1C-4D5E-6F7A-8B9C-0D1E2F3A4B5C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\DiaryApp
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=
OutputDir=installer_output
OutputBaseFilename=DiaryApp_Setup
SetupIconFile=
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Main executable
Source: "dist\diary_app.exe"; DestDir: "{app}"; Flags: ignoreversion

; Configuration files
Source: "config.example.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "config.example.py"; DestDir: "{app}"; DestName: "config.py"; Flags: onlyifdoesntexist uninsneveruninstall

; Task scheduler scripts
Source: "install_tasks.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "uninstall_tasks.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "restart_service.bat"; DestDir: "{app}"; Flags: ignoreversion

; DiaryEditor - Database editor tool
Source: "DiaryEditor\*"; DestDir: "{app}\DiaryEditor"; Flags: ignoreversion recursesubdirs createallsubdirs

; Documentation (optional - if you want to include)
; Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Dirs]
; Create necessary directories
Name: "{app}\instance"; Permissions: users-full
Name: "{app}\logs"; Permissions: users-full
Name: "{app}\reports"; Permissions: users-full
Name: "{app}\reports\PDF"; Permissions: users-full
Name: "{app}\reports\CSV"; Permissions: users-full
Name: "{app}\templates"; Permissions: users-full

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{group}\Database Editor"; Filename: "{app}\DiaryEditor\start_editor.bat"; WorkingDir: "{app}\DiaryEditor"; Comment: "Edit past diary occurrences"
Name: "{group}\Configure Email Settings"; Filename: "notepad.exe"; Parameters: """{app}\config.py"""
Name: "{group}\View Logs"; Filename: "{app}\logs"
Name: "{group}\View Reports"; Filename: "{app}\reports"

[Run]
; Install Windows Task Scheduler tasks
Filename: "{app}\install_tasks.bat"; Parameters: """{app}"""; StatusMsg: "Installing scheduled tasks..."; Flags: runhidden waituntilterminated

; Start the application after installation
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Remove scheduled tasks and stop application before uninstall
Filename: "{app}\uninstall_tasks.bat"; Flags: runhidden waituntilterminated

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // Additional post-install tasks can be added here
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    // Stop the application before uninstalling
    Exec('taskkill', '/IM diary_app.exe /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

[Messages]
WelcomeLabel2=This will install [name/ver] on your computer.%n%nThe application will automatically start on Windows boot and restart daily at 01:00 AM to ensure optimal performance.%n%nIt is recommended that you close all other applications before continuing.

