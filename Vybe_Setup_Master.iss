[Setup]
AppId={{B8E8F7A2-1234-4567-8901-123456789012}
AppName=Vybe AI Assistant
AppVersion=0.8
AppVerName=Vybe AI Assistant 0.8 ALPHA
AppPublisher=Vybe Team
AppPublisherURL=https://github.com/socalcium/Vybe-Local-Agentic-Container
AppSupportURL=https://github.com/socalcium/Vybe-Local-Agentic-Container/issues
AppUpdatesURL=https://github.com/socalcium/Vybe-Local-Agentic-Container/releases
DefaultDirName={autopf}\Vybe AI Assistant
DefaultGroupName=Vybe AI Assistant
AllowNoIcons=yes
LicenseFile=LICENSE
InfoBeforeFile=INSTALLATION_GUIDE.md
InfoAfterFile=README.md
OutputDir=dist
OutputBaseFilename=Vybe_Setup_v0.8_ALPHA
SetupIconFile=assets\VybeLight.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
MinVersion=10.0
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
DisableDirPage=no
DisableProgramGroupPage=no
UninstallDisplayIcon={app}\assets\VybeLight.ico
UninstallDisplayName=Vybe AI Assistant 0.8 ALPHA

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "full"; Description: "Full Installation (Recommended)"
Name: "minimal"; Description: "Minimal Installation"
Name: "custom"; Description: "Custom Installation"; Flags: iscustom

[Components]
Name: "core"; Description: "Core Application Files"; Types: full minimal custom; Flags: fixed
Name: "desktop"; Description: "Desktop Application (Tauri)"; Types: full custom
Name: "models"; Description: "Default AI Model (637MB)"; Types: full custom; ExtraDiskSpaceRequired: 668000000
Name: "docs"; Description: "Documentation and Guides"; Types: full custom
Name: "shortcuts"; Description: "Desktop and Start Menu Shortcuts"; Types: full custom

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; Components: shortcuts
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Components: shortcuts
Name: "startmenu"; Description: "Add to Start Menu"; GroupDescription: "{cm:AdditionalIcons}"; Components: shortcuts
Name: "systemtray"; Description: "Start with Windows (System Tray)"; GroupDescription: "Startup Options"; Flags: unchecked

[Files]
; Core Installation Scripts
Source: "{tmp}\setup_python_env.bat"; DestDir: "{app}"; Flags: ignoreversion external; Components: core
Source: "{tmp}\installer_backend.py"; DestDir: "{app}"; Flags: ignoreversion external; Components: core
Source: "{tmp}\download_default_model.py"; DestDir: "{app}"; Flags: ignoreversion external; Components: core
Source: "{tmp}\run.py"; DestDir: "{app}"; Flags: ignoreversion external; Components: core
Source: "{tmp}\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion external; Components: core
Source: "{tmp}\pyproject.toml"; DestDir: "{app}"; Flags: ignoreversion external; Components: core

; Launch Scripts
Source: "{tmp}\launch_vybe_master.bat"; DestDir: "{app}"; Flags: ignoreversion external; Components: core
Source: "{tmp}\shutdown.bat"; DestDir: "{app}"; Flags: ignoreversion external; Components: core
Source: "{tmp}\shutdown_quiet.bat"; DestDir: "{app}"; Flags: ignoreversion external; Components: core

; Documentation
Source: "{tmp}\README.md"; DestDir: "{app}"; Flags: ignoreversion external; Components: docs
Source: "{tmp}\LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion external; Components: docs

[Dirs]
Name: "{app}\instance"; Permissions: users-full
Name: "{app}\workspace"; Permissions: users-full
Name: "{app}\models"; Permissions: users-full
Name: "{app}\logs"; Permissions: users-full
Name: "{app}\temp"; Permissions: users-full

[Icons]
; Start Menu
Name: "{group}\Vybe AI Assistant"; Filename: "{app}\launch_vybe_master.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\VybeLight.ico"; Components: shortcuts
Name: "{group}\Vybe Desktop"; Filename: "{app}\vybe-desktop\vybe-desktop.exe"; WorkingDir: "{app}\vybe-desktop"; IconFilename: "{app}\assets\VybeLight.ico"; Components: desktop and shortcuts
Name: "{group}\{cm:UninstallProgram,Vybe AI Assistant}"; Filename: "{uninstallexe}"; Components: shortcuts

; Desktop
Name: "{autodesktop}\Vybe AI Assistant"; Filename: "{app}\launch_vybe.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\VybeLight.ico"; Tasks: desktopicon
Name: "{autodesktop}\Vybe Desktop"; Filename: "{app}\vybe-desktop\vybe-desktop.exe"; WorkingDir: "{app}\vybe-desktop"; IconFilename: "{app}\assets\VybeLight.ico"; Tasks: desktopicon; Components: desktop

; Quick Launch
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\Vybe AI"; Filename: "{app}\launch_vybe.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\VybeLight.ico"; Tasks: quicklaunchicon

[Registry]
; Add to Windows Path (optional)
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Check: NeedsAddPath('{app}')

; File associations (optional)
Root: HKCR; Subkey: ".vybe"; ValueType: string; ValueName: ""; ValueData: "VybeProject"
Root: HKCR; Subkey: "VybeProject"; ValueType: string; ValueName: ""; ValueData: "Vybe AI Project"
Root: HKCR; Subkey: "VybeProject\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\assets\VybeLight.ico"
Root: HKCR; Subkey: "VybeProject\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\launch_vybe.bat"" ""%1"""

; Startup registry entry (if selected)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "VybeAI"; ValueData: """{app}\launch_vybe.bat"" --minimized"; Tasks: systemtray

[Run]
; Download files from GitHub
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -Command ""Write-Host 'Downloading Vybe from GitHub...'; try {{ Invoke-WebRequest -Uri 'https://github.com/socalcium/Vybe-Local-Agentic-Container/archive/refs/heads/main.zip' -OutFile '{tmp}\vybe-main.zip' -UseBasicParsing; Write-Host 'Download completed successfully' }} catch {{ Write-Host 'Download failed:' $_.Exception.Message; exit 1 }}"""; WorkingDir: "{tmp}"; Flags: waituntilterminated; StatusMsg: "Downloading application files from GitHub..."

; Extract downloaded files
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -Command ""Write-Host 'Extracting application files...'; try {{ Expand-Archive -Path '{tmp}\vybe-main.zip' -DestinationPath '{tmp}' -Force; Write-Host 'Extraction completed' }} catch {{ Write-Host 'Extraction failed:' $_.Exception.Message; exit 1 }}"""; WorkingDir: "{tmp}"; Flags: waituntilterminated; StatusMsg: "Extracting application files..."

; Copy application files to installation directory
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -Command ""Write-Host 'Installing application files...'; try {{ $src = '{tmp}\Vybe-Local-Agentic-Container-main'; $dst = '{app}'; if (Test-Path $src) {{ Copy-Item -Path '$src\*' -Destination $dst -Recurse -Force; Write-Host 'Application files installed successfully' }} else {{ Write-Host 'Source directory not found'; exit 1 }} }} catch {{ Write-Host 'Installation failed:' $_.Exception.Message; exit 1 }}"""; WorkingDir: "{app}"; Flags: waituntilterminated; StatusMsg: "Installing application files..."

; Download and install Python if needed
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -Command ""if (-not (Get-Command python -ErrorAction SilentlyContinue)) {{ Write-Host 'Downloading Python 3.11...'; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '{tmp}\python-installer.exe' -UseBasicParsing; Write-Host 'Installing Python...'; Start-Process '{tmp}\python-installer.exe' -ArgumentList '/quiet','InstallAllUsers=1','PrependPath=1','Include_test=0' -Wait }} else {{ Write-Host 'Python already installed' }}"""; WorkingDir: "{tmp}"; Flags: waituntilterminated; StatusMsg: "Installing Python 3.11..."; Check: not IsPythonInstalled

; Setup Python environment and install dependencies
Filename: "{app}\setup_python_env.bat"; Parameters: ""; StatusMsg: "Setting up Python environment..."; Flags: runhidden waituntilterminated; WorkingDir: "{app}"

; Download default model (if component selected)
Filename: "python"; Parameters: """{app}\download_default_model.py"""; StatusMsg: "Downloading default AI model (this may take several minutes)..."; Flags: runhidden waituntilterminated; WorkingDir: "{app}"; Components: models; Check: HasInternetConnection

; Build Tauri desktop app (if component selected)
Filename: "{app}\vybe-desktop\build.bat"; Parameters: ""; StatusMsg: "Building desktop application..."; Flags: runhidden waituntilterminated; WorkingDir: "{app}\vybe-desktop"; Components: desktop; Check: HasNodeJS

; First launch setup
Filename: "python"; Parameters: """{app}\run.py"" --setup"; StatusMsg: "Running first-time setup..."; Flags: runhidden waituntilterminated; WorkingDir: "{app}"

[UninstallRun]
; Clean shutdown
Filename: "{app}\shutdown_quiet.bat"; Parameters: ""; Flags: runhidden waituntilterminated; RunOnceId: "VybeShutdown"

[UninstallDelete]
; Clean up generated files
Type: filesandordirs; Name: "{app}\instance"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\temp"
Type: filesandordirs; Name: "{app}\vybe-env-*"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\*.pyc"

[Code]
function IsPythonInstalled: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('python', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

function HasNodeJS: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('node', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

function HasInternetConnection: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('ping', 'google.com -n 1', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

function NeedsAddPath(Param: string): Boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_LOCAL_MACHINE, 'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 'Path', OrigPath) then begin
    Result := True;
    exit;
  end;
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
  PythonVersion: string;
begin
  if CurStep = ssPostInstall then
  begin
    // Verify Python installation
    if Exec('python', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    begin
      MsgBox('Python installation verified successfully!', mbInformation, MB_OK);
    end else
    begin
      MsgBox('Warning: Python installation could not be verified. Some features may not work.', mbError, MB_OK);
    end;
    
    // Create initial configuration
    Exec('python', ExpandConstant('"{app}\installer_backend.py" --init'), '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  
  if CurPageID = wpSelectComponents then
  begin
    if not WizardIsComponentSelected('models') then
    begin
      if MsgBox('You have chosen not to install the default AI model. You will need to download models manually later. Continue?', mbConfirmation, MB_YESNO) = IDNO then
      begin
        Result := False;
      end;
    end;
  end;
  
  if CurPageID = wpReady then
  begin
    if not IsPythonInstalled then
    begin
      MsgBox('Python 3.11 will be installed automatically. This may take a few minutes.', mbInformation, MB_OK);
    end;
  end;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  
  // Check Windows version
  if GetWindowsVersion < $0A000000 then  // Windows 10+
  begin
    MsgBox('This application requires Windows 10 or later.', mbError, MB_OK);
    Result := False;
  end;
  
  // Check if already installed
  if RegKeyExists(HKEY_LOCAL_MACHINE, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{B8E8F7A2-1234-4567-8901-123456789012}_is1') then
  begin
    if MsgBox('Vybe AI Assistant appears to already be installed. Do you want to reinstall?', mbConfirmation, MB_YESNO) = IDNO then
    begin
      Result := False;
    end;
  end;
end;

procedure InitializeWizard();
begin
  WizardForm.LicenseAcceptedRadio.Checked := True;
end;