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
Name: "models"; Description: "Default AI Model (637MB)"; Types: full custom; ExtraDiskSpaceRequired: 668000000
Name: "docs"; Description: "Documentation and Guides"; Types: full custom
Name: "shortcuts"; Description: "Desktop and Start Menu Shortcuts"; Types: full custom

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; Components: shortcuts
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Components: shortcuts
Name: "startmenu"; Description: "Add to Start Menu"; GroupDescription: "{cm:AdditionalIcons}"; Components: shortcuts
Name: "systemtray"; Description: "Start with Windows (System Tray)"; GroupDescription: "Startup Options"; Flags: unchecked

[Files]
; No files are copied during installation - everything is downloaded from GitHub during the [Run] phase

[Dirs]
Name: "{app}\instance"; Permissions: users-full
Name: "{app}\workspace"; Permissions: users-full
Name: "{app}\models"; Permissions: users-full
Name: "{app}\logs"; Permissions: users-full
Name: "{app}\temp"; Permissions: users-full

[Icons]
; Start Menu
Name: "{group}\Vybe AI Assistant"; Filename: "{app}\launch_vybe_master.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\VybeLight.ico"; Components: shortcuts
Name: "{group}\{cm:UninstallProgram,Vybe AI Assistant}"; Filename: "{uninstallexe}"; Components: shortcuts

; Desktop
Name: "{autodesktop}\Vybe AI Assistant"; Filename: "{app}\launch_vybe_master.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\VybeLight.ico"; Tasks: desktopicon

; Quick Launch
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\Vybe AI"; Filename: "{app}\launch_vybe_master.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\VybeLight.ico"; Tasks: quicklaunchicon

[Registry]
; Add to Windows Path (optional)
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Check: NeedsAddPath('{app}')

; File associations (optional)
Root: HKCR; Subkey: ".vybe"; ValueType: string; ValueName: ""; ValueData: "VybeProject"
Root: HKCR; Subkey: "VybeProject"; ValueType: string; ValueName: ""; ValueData: "Vybe AI Project"
Root: HKCR; Subkey: "VybeProject\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\assets\VybeLight.ico"
Root: HKCR; Subkey: "VybeProject\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\launch_vybe_master.bat"" ""%1"""

; Startup registry entry (if selected)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "VybeAI"; ValueData: """{app}\launch_vybe_master.bat"" --minimized"; Tasks: systemtray

[Run]
; Download files from GitHub (silent)
Filename: "powershell.exe"; Parameters: "-WindowStyle Hidden -ExecutionPolicy Bypass -Command ""try {{ Invoke-WebRequest -Uri 'https://github.com/socalcium/Vybe-Local-Agentic-Container/archive/refs/heads/master.zip' -OutFile '{tmp}\vybe-master.zip' -UseBasicParsing }} catch {{ exit 1 }}"""; WorkingDir: "{tmp}"; Flags: runhidden waituntilterminated; StatusMsg: "Downloading application files from GitHub..."

; Extract downloaded files (silent)
Filename: "powershell.exe"; Parameters: "-WindowStyle Hidden -ExecutionPolicy Bypass -Command ""try {{ Expand-Archive -Path '{tmp}\vybe-master.zip' -DestinationPath '{tmp}' -Force }} catch {{ exit 1 }}"""; WorkingDir: "{tmp}"; Flags: runhidden waituntilterminated; StatusMsg: "Extracting application files..."

; Copy application files to installation directory (silent)
Filename: "powershell.exe"; Parameters: "-WindowStyle Hidden -ExecutionPolicy Bypass -Command ""try {{ $src = '{tmp}\Vybe-Local-Agentic-Container-master'; $dst = '{app}'; if (Test-Path $src) {{ Copy-Item -Path '$src\*' -Destination $dst -Recurse -Force }} else {{ exit 1 }} }} catch {{ exit 1 }}"""; WorkingDir: "{app}"; Flags: runhidden waituntilterminated; StatusMsg: "Installing application files..."

; Download and install Python silently if needed
Filename: "powershell.exe"; Parameters: "-WindowStyle Hidden -ExecutionPolicy Bypass -Command ""if (-not (Get-Command python -ErrorAction SilentlyContinue)) {{ Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '{tmp}\python-installer.exe' -UseBasicParsing; Start-Process '{tmp}\python-installer.exe' -ArgumentList '/quiet','InstallAllUsers=1','PrependPath=1','Include_test=0' -Wait; $env:Path = [System.Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [System.Environment]::GetEnvironmentVariable('Path','User') }}"""; WorkingDir: "{tmp}"; Flags: runhidden waituntilterminated; StatusMsg: "Installing Python 3.11..."; Check: not IsPythonInstalled

; Create virtual environment and install all requirements (silent)
Filename: "powershell.exe"; Parameters: "-WindowStyle Hidden -ExecutionPolicy Bypass -Command ""try {{ Set-Location '{app}'; $pythonCmd = if (Get-Command python -ErrorAction SilentlyContinue) {{ 'python' }} else {{ 'C:\Program Files\Python311\python.exe' }}; & $pythonCmd -m venv vybe-env; & '{app}\vybe-env\Scripts\python.exe' -m pip install --upgrade pip; & '{app}\vybe-env\Scripts\python.exe' -m pip install -r requirements.txt }} catch {{ Write-Host 'Error:' $_.Exception.Message; exit 1 }}"""; StatusMsg: "Installing Python dependencies..."; Flags: runhidden waituntilterminated; WorkingDir: "{app}"

; Download default model (if component selected)
Filename: "powershell.exe"; Parameters: "-WindowStyle Hidden -ExecutionPolicy Bypass -Command ""try {{ Set-Location '{app}'; & '{app}\vybe-env\Scripts\python.exe' download_default_model.py }} catch {{ Write-Host 'Model download failed but continuing installation...' }}"""; StatusMsg: "Downloading default AI model (this may take several minutes)..."; Flags: runhidden waituntilterminated; WorkingDir: "{app}"; Components: models; Check: HasInternetConnection

; Create necessary instance directories
Filename: "powershell.exe"; Parameters: "-WindowStyle Hidden -ExecutionPolicy Bypass -Command ""try {{ Set-Location '{app}'; New-Item -ItemType Directory -Path 'instance' -Force | Out-Null; New-Item -ItemType Directory -Path 'logs' -Force | Out-Null; New-Item -ItemType Directory -Path 'models' -Force | Out-Null; Write-Host 'Directories created successfully' }} catch {{ Write-Host 'Directory creation error:' $_.Exception.Message }}"""; StatusMsg: "Creating application directories..."; Flags: runhidden waituntilterminated; WorkingDir: "{app}"

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