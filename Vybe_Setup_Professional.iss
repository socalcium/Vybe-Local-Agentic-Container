; Vybe AI Assistant Professional Setup Script
; Enhanced with status window, error handling, and silent operations

#define MyAppName "Vybe AI Assistant"
#define MyAppVersion "0.8"
#define MyAppPublisher "Vybe Team"
#define MyAppURL "https://github.com/socalcium/Vybe-Local-Agentic-Container"
#define MyAppExeName "launch_vybe_master.bat"
#define MinPythonVersion "3.9"

[Setup]
; App Information
AppId={{B8E8F7A2-1234-4567-8901-123456789012}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion} Professional
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases

; Installation Settings
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
DisableProgramGroupPage=no
DisableDirPage=no

; Output Settings
OutputDir=dist
OutputBaseFilename=Vybe_Setup_v{#MyAppVersion}_Professional
SetupIconFile=assets\VybeLight.ico
; WizardImageFile=assets\VybeLight1024.png
; WizardSmallImageFile=assets\VybeLight.ico

; Compression
Compression=lzma2/ultra64
SolidCompression=yes
CompressionThreads=auto

; UI Settings
WizardStyle=modern
DisableWelcomePage=no
DisableReadyPage=no
DisableFinishedPage=no
ShowLanguageDialog=no

; Privileges
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; System Requirements
MinVersion=10.0
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Uninstall
UninstallDisplayIcon={app}\assets\VybeLight.ico
UninstallDisplayName={#MyAppName} {#MyAppVersion}
CreateUninstallRegKey=yes

; Signing (optional - configure with your certificate)
; SignTool=signtool /f "path\to\certificate.pfx" /p password /t http://timestamp.digicert.com /d $q{#MyAppName}$q $f

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Types]
Name: "full"; Description: "Full Installation (Recommended)"
Name: "minimal"; Description: "Minimal Installation"
Name: "custom"; Description: "Custom Installation"; Flags: iscustom

[Components]
Name: "core"; Description: "Core Application Files"; Types: full minimal custom; Flags: fixed
Name: "models"; Description: "Orchestrator Models (Backend AI)"; Types: full custom
Name: "models\tier1"; Description: "Tier 1: Dolphin Phi-2 2.7B (8GB GPU - 1.6GB)"; Types: full; ExtraDiskSpaceRequired: 1677721600
Name: "models\tier2"; Description: "Tier 2: Dolphin Mistral 7B (10GB GPU - 4.1GB)"; Types: custom; ExtraDiskSpaceRequired: 4294967296
Name: "models\tier3"; Description: "Tier 3: Hermes Llama3 8B (16GB GPU - 4.8GB)"; Types: custom; ExtraDiskSpaceRequired: 5033164800
Name: "desktop"; Description: "Desktop Application (Tauri)"; Types: full custom
Name: "docs"; Description: "Documentation and Guides"; Types: full custom
Name: "examples"; Description: "Example Plugins and Scripts"; Types: full custom

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; OnlyBelowVersion: 0
Name: "startupicon"; Description: "Start automatically with Windows"; GroupDescription: "Startup Options"; Flags: unchecked
Name: "envpath"; Description: "Add to system PATH"; GroupDescription: "Environment"; Flags: unchecked

[Files]
; Core installer files - these must be included in the setup
Source: "installer_status_window.py"; DestDir: "{tmp}"; Flags: dontcopy
Source: "LICENSE"; DestDir: "{tmp}"; Flags: dontcopy
Source: "assets\VybeLight.ico"; DestDir: "{tmp}"; Flags: dontcopy

; Placeholder for downloaded files - actual files are downloaded during installation
; This section will be populated by the installer dynamically

[Dirs]
; Create application directories with proper permissions
Name: "{app}"
Name: "{app}\instance"
Name: "{app}\logs"
Name: "{app}\models"
Name: "{app}\workspace"
Name: "{app}\rag_data"
Name: "{app}\rag_data\chroma_db"
Name: "{app}\rag_data\knowledge_base"
Name: "{app}\temp"
Name: "{app}\plugins"

[Icons]
; Start Menu Icons
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\VybeLight.ico"; Comment: "Launch Vybe AI Assistant"
Name: "{group}\Vybe Documentation"; Filename: "{app}\docs\MASTER_DOCUMENTATION_INDEX.md"; Comment: "View Documentation"; Components: docs
Name: "{group}\Vybe Configuration"; Filename: "{app}\.env"; Comment: "Edit Configuration"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"

; Desktop Icon
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\VybeLight.ico"; Tasks: desktopicon; Comment: "Launch Vybe AI Assistant"

; Quick Launch Icon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\assets\VybeLight.ico"; Tasks: quicklaunchicon

[Registry]
; File Association for .vybe files
Root: HKCR; Subkey: ".vybe"; ValueType: string; ValueName: ""; ValueData: "VybeProject"; Flags: uninsdeletevalue
Root: HKCR; Subkey: "VybeProject"; ValueType: string; ValueName: ""; ValueData: "Vybe AI Project"; Flags: uninsdeletekey
Root: HKCR; Subkey: "VybeProject\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\assets\VybeLight.ico"
Root: HKCR; Subkey: "VybeProject\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

; Add to PATH (optional)
Root: HKLM; Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Tasks: envpath; Check: NeedsAddPath('{app}')

; Application Settings (system-wide)
Root: HKLM; Subkey: "Software\Vybe AI"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "Software\Vybe AI"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"

[Run]
; Main installation process with custom status window (includes model download)
Filename: "{tmp}\run_installer.bat"; Parameters: ""; StatusMsg: "Installing Vybe AI Assistant..."; Flags: runhidden waituntilterminated; BeforeInstall: ExtractInstaller

; Desktop app build (optional)
Filename: "{app}\build_desktop.bat"; WorkingDir: "{app}"; StatusMsg: "Building desktop application..."; Flags: runhidden skipifdoesntexist; Components: desktop; Check: FileExists(ExpandConstant('{app}\build_desktop.bat'))

[UninstallRun]
; Graceful shutdown before uninstall
Filename: "{app}\shutdown_quiet.bat"; Parameters: ""; Flags: runhidden waituntilterminated skipifdoesntexist; RunOnceId: "ShutdownVybe"

[UninstallDelete]
; Clean up generated files and directories
Type: filesandordirs; Name: "{app}\instance"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\temp"
Type: filesandordirs; Name: "{app}\workspace"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: filesandordirs; Name: "{app}\vybe-env*"
Type: files; Name: "{app}\*.pyc"
Type: files; Name: "{app}\*.pyo"
Type: files; Name: "{app}\.env"
Type: dirifempty; Name: "{app}"

[Code]
var
  PythonInstallPage: TOutputProgressWizardPage;
  InstallSuccess: Boolean;
  
function InitializeSetup(): Boolean;
var
  Version: TWindowsVersion;
begin
  Result := True;
  InstallSuccess := False;
  
  // Check Windows version
  GetWindowsVersionEx(Version);
  if Version.Major < 10 then
  begin
    MsgBox('Vybe AI Assistant requires Windows 10 or later.', mbError, MB_OK);
    Result := False;
    Exit;
  end;
  
  // Check for existing installation
  if RegKeyExists(HKEY_LOCAL_MACHINE, 'Software\Vybe AI') then
  begin
    if MsgBox('Vybe AI Assistant appears to be already installed. Do you want to reinstall?' + #13#10 + 
              'This will preserve your data and settings.', mbConfirmation, MB_YESNO) = IDNO then
    begin
      Result := False;
    end;
  end;
end;

procedure InitializeWizard();
begin
  // Create custom pages
  PythonInstallPage := CreateOutputProgressPage('Python Installation', 
    'The setup is checking and installing Python if needed...');
    
  // Modern UI customizations
  WizardForm.WelcomeLabel1.Font.Size := 12;
  WizardForm.WelcomeLabel1.Font.Style := [fsBold];
  WizardForm.PageNameLabel.Font.Size := 10;
  WizardForm.PageDescriptionLabel.Font.Size := 9;
end;

function NeedsAddPath(Param: string): Boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_LOCAL_MACHINE, 
    'SYSTEM\CurrentControlSet\Control\Session Manager\Environment', 
    'Path', OrigPath) then
  begin
    Result := True;
    Exit;
  end;
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;

function GetModelDownloadFlag(): String;
begin
  // Check if any model tier is selected
  if WizardIsComponentSelected('models\tier1') or WizardIsComponentSelected('models\tier2') or WizardIsComponentSelected('models\tier3') then
    Result := 'true'
  else
    Result := 'false';
end;

function FileReplaceString(const FileName, SearchString, ReplaceString: string): Boolean;
var
  FileContent: String;
  AnsiContent: AnsiString;
begin
  Result := False;
  if LoadStringFromFile(FileName, AnsiContent) then
  begin
    FileContent := String(AnsiContent);
    StringChangeEx(FileContent, SearchString, ReplaceString, True);
    Result := SaveStringToFile(FileName, AnsiString(FileContent), False);
  end;
end;

procedure ExtractInstaller();
var
  StatusScript: string;
begin
  // Extract Python installer status window
  ExtractTemporaryFile('installer_status_window.py');
  ExtractTemporaryFile('LICENSE');
  ExtractTemporaryFile('VybeLight.ico');
  
  // Create a Python runner batch file that properly runs the installer
  StatusScript := ExpandConstant('{tmp}\run_installer.bat');
  SaveStringToFile(StatusScript, 
    '@echo off' + #13#10 +
    'echo Starting Vybe AI Assistant Installation...' + #13#10 +
    'cd /d "' + ExpandConstant('{tmp}') + '"' + #13#10 +
    'echo Trying to run installer with Python...' + #13#10 +
    '' + #13#10 +
    'REM Determine if models should be downloaded' + #13#10 +
    'set MODEL_FLAG=' + #13#10 +
    'if "' + GetModelDownloadFlag() + '" == "true" set MODEL_FLAG=--download-models' + #13#10 +
    'if "' + GetModelDownloadFlag() + '" == "false" set MODEL_FLAG=--no-models' + #13#10 +
    '' + #13#10 +
    'REM Try different Python commands' + #13#10 +
    'python installer_status_window.py "' + ExpandConstant('{app}') + '" %MODEL_FLAG%' + #13#10 +
    'if %ERRORLEVEL% EQU 0 goto :success' + #13#10 +
    '' + #13#10 +
    'py -3 installer_status_window.py "' + ExpandConstant('{app}') + '" %MODEL_FLAG%' + #13#10 +
    'if %ERRORLEVEL% EQU 0 goto :success' + #13#10 +
    '' + #13#10 +
    'py -3.11 installer_status_window.py "' + ExpandConstant('{app}') + '" %MODEL_FLAG%' + #13#10 +
    'if %ERRORLEVEL% EQU 0 goto :success' + #13#10 +
    '' + #13#10 +
    '"C:\Program Files\Python311\python.exe" installer_status_window.py "' + ExpandConstant('{app}') + '" %MODEL_FLAG%' + #13#10 +
    'if %ERRORLEVEL% EQU 0 goto :success' + #13#10 +
    '' + #13#10 +
    '"C:\Program Files\Python310\python.exe" installer_status_window.py "' + ExpandConstant('{app}') + '" %MODEL_FLAG%' + #13#10 +
    'if %ERRORLEVEL% EQU 0 goto :success' + #13#10 +
    '' + #13#10 +
    'echo ERROR: Could not find Python to run the installer!' + #13#10 +
    'echo Please install Python 3.9+ and try again.' + #13#10 +
    'pause' + #13#10 +
    'exit /b 1' + #13#10 +
    '' + #13#10 +
    ':success' + #13#10 +
    'echo Installation completed successfully!' + #13#10 +
    'exit /b 0', False);
end;

function CheckPythonInstalled(): Boolean;
var
  ResultCode: Integer;
begin
  Result := False;
  
  // Try various Python commands
  if Exec('python', '--version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0) then
    Result := True
  else if Exec('py', '-3 --version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0) then
    Result := True
  else if FileExists('C:\Program Files\Python311\python.exe') then
    Result := True
  else if FileExists('C:\Program Files\Python310\python.exe') then
    Result := True
  else if FileExists('C:\Program Files\Python39\python.exe') then
    Result := True;
end;

procedure InstallPython();
var
  ResultCode: Integer;
begin
  if not CheckPythonInstalled() then
  begin
    // Python not found, show message and open Python download page
    if MsgBox('Python 3.9 or later is required but was not found on your system.' + #13#10 + #13#10 +
              'Would you like to download Python now?' + #13#10 + #13#10 +
              'Click Yes to open the Python download page, or No to exit setup.', 
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      // Open Python download page
      Exec('https://www.python.org/downloads/', '', '', SW_SHOW, ewNoWait, ResultCode);
      MsgBox('Please download and install Python 3.11 (64-bit), then run this installer again.' + #13#10 + #13#10 +
             'IMPORTANT: During Python installation, make sure to check "Add Python to PATH"!', 
             mbInformation, MB_OK);
    end;
    
    // Exit setup
    WizardForm.Close;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  case CurStep of
    ssInstall:
      begin
        // Install Python if needed before main installation
        InstallPython();
        
        // Verify Python is available
        if not CheckPythonInstalled() then
        begin
          MsgBox('Python installation is required to continue. Please install Python 3.9 or later and run setup again.', 
                 mbError, MB_OK);
          WizardForm.Close;
        end;
      end;
      
    ssPostInstall:
      begin
        // Verify installation completed successfully
        if FileExists(ExpandConstant('{app}\instance\setup_complete.flag')) then
        begin
          InstallSuccess := True;
          
          // Set up Windows Defender exclusions (optional, requires admin)
          Exec('powershell.exe', 
               '-Command "Add-MpPreference -ExclusionPath ''' + ExpandConstant('{app}') + ''' -ErrorAction SilentlyContinue"',
               '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
        end
        else
        begin
          MsgBox('Installation may not have completed successfully. Please check the installation log for errors.', 
                 mbInformation, MB_OK);
        end;
      end;
      
    ssDone:
      begin
        // Open documentation or quick start guide
        if InstallSuccess and WizardIsComponentSelected('docs') then
        begin
          if MsgBox('Would you like to view the Quick Start Guide?', mbConfirmation, MB_YESNO) = IDYES then
          begin
            Exec('notepad.exe', ExpandConstant('"{app}\docs\getting-started\complete-installation-guide.md"'), 
                 '', SW_SHOW, ewNoWait, ResultCode);
          end;
        end;
      end;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
begin
  Result := '';
  NeedsRestart := False;
  
  // Check for running instances
  if FileExists(ExpandConstant('{app}\vybe.lock')) then
  begin
    if MsgBox('Vybe AI Assistant appears to be running. Would you like Setup to close it?', 
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      Exec(ExpandConstant('{app}\shutdown_quiet.bat'), '', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
      Sleep(2000);
    end
    else
    begin
      Result := 'Please close Vybe AI Assistant before continuing with the installation.';
    end;
  end;
end;

function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo, MemoTypeInfo,
  MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
var
  S: String;
begin
  S := '';
  
  S := S + 'Installation Summary:' + NewLine + NewLine;
  
  S := S + MemoDirInfo + NewLine + NewLine;
  
  if MemoComponentsInfo <> '' then
    S := S + 'Selected Components:' + NewLine + MemoComponentsInfo + NewLine;
    
  if MemoTasksInfo <> '' then
    S := S + 'Additional Tasks:' + NewLine + MemoTasksInfo + NewLine;
    
  S := S + NewLine + 'The installer will:' + NewLine;
  S := S + '• Download the latest Vybe AI Assistant from GitHub' + NewLine;
  S := S + '• Install Python 3.11 if not already installed' + NewLine;
  S := S + '• Create a virtual environment and install dependencies' + NewLine;
  S := S + '• Configure the application for first use' + NewLine;
  
  if WizardIsComponentSelected('models\tier1') or WizardIsComponentSelected('models\tier2') or WizardIsComponentSelected('models\tier3') then
    S := S + '• Download selected AI models (this may take some time)' + NewLine;
    
  Result := S;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DeleteDataChoice: Integer;
begin
  case CurUninstallStep of
    usUninstall:
      begin
        // Ask user about data deletion
        DeleteDataChoice := MsgBox('Do you want to remove all Vybe data including:' + #13#10 +
                                  '• Chat history and conversations' + #13#10 +
                                  '• Downloaded AI models' + #13#10 +
                                  '• Custom configurations' + #13#10 +
                                  '• Knowledge base data' + #13#10#13#10 +
                                  'Select "Yes" to remove all data, or "No" to keep your data for future use.',
                                  mbConfirmation, MB_YESNO);
        
        if DeleteDataChoice = IDNO then
        begin
          // Preserve user data by moving it temporarily
          RenameFile(ExpandConstant('{app}\instance'), ExpandConstant('{app}\instance.backup'));
          RenameFile(ExpandConstant('{app}\models'), ExpandConstant('{app}\models.backup'));
          RenameFile(ExpandConstant('{app}\rag_data'), ExpandConstant('{app}\rag_data.backup'));
        end;
      end;
      
    usPostUninstall:
      begin
        // Restore preserved data if user chose to keep it
        if DirExists(ExpandConstant('{app}\instance.backup')) then
        begin
          RenameFile(ExpandConstant('{app}\instance.backup'), ExpandConstant('{app}\instance'));
          RenameFile(ExpandConstant('{app}\models.backup'), ExpandConstant('{app}\models'));
          RenameFile(ExpandConstant('{app}\rag_data.backup'), ExpandConstant('{app}\rag_data'));
          
          MsgBox('Your Vybe data has been preserved in: ' + ExpandConstant('{app}') + #13#10 +
                 'You can manually delete this folder later if desired.', mbInformation, MB_OK);
        end;
      end;
  end;
end;
