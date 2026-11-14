; Inno Setup 6 script for RDP Nexus.
;
; THIS FILE IS NOT THE INSTALLER.  To install RDP Nexus, download RDPNexus-setup.exe from
; https://github.com/cleanstateweb-eng/RDP-Nexus/releases/latest and double-click it.
;
; It packages an already-built program.  scripts\build_windows.bat builds the program and then
; compiles this script (passing /DAppVersion, /DSourceDir and /DOutputDir).
; Per-user install (no administrator rights): {autopf} resolves to %LOCALAPPDATA%\Programs.

#ifndef SourceDir
  #define SourceDir "..\dist\RDPNexus"
#endif
#ifndef OutputDir
  #define OutputDir "..\release"
#endif

#define AppName "RDP Nexus"
#define AppExe "RDPNexus.exe"
#define AppPublisher "RDP Nexus"
#define AppURL "https://github.com/cleanstateweb-eng/RDP-Nexus"

; Opened straight from a downloaded copy of the source?  Then there is nothing to package yet.
#define SourceProbe (Pos(":", SourceDir) > 0 ? SourceDir : AddBackslash(SourcePath) + SourceDir)
#if !FileExists(AddBackslash(SourceProbe) + AppExe)
  #error RDP Nexus has not been built yet, so there is nothing to package. To INSTALL it, download RDPNexus-setup.exe from https://github.com/cleanstateweb-eng/RDP-Nexus/releases/latest and double-click it. To BUILD it yourself, run scripts\build_windows.bat instead of opening this file.
#endif
#ifndef AppVersion
  ; Compiled by hand: take the version from the built program (1.0.5.0 -> 1.0.5).
  #define ExeVersion GetVersionNumbersString(AddBackslash(SourceProbe) + AppExe)
  #define AppVersion Copy(ExeVersion, 1, RPos(".", ExeVersion) - 1)
#endif

[Setup]
AppId={{8F3C2B71-5D7A-4E8B-9C21-6A4D3E2F1B90}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
VersionInfoVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#OutputDir}
OutputBaseFilename=RDPNexus-{#AppVersion}-setup
SetupIconFile=..\assets\app.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
; One double-click installs: no wizard pages, just a progress window, then RDP Nexus starts.
DisableWelcomePage=yes
DisableDirPage=yes
DisableReadyPage=yes
DisableFinishedPage=yes
; A running RDP Nexus (an upgrade) is closed automatically instead of asking (see [Code]).
CloseApplications=no
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; Comment: "RDP-only keyboard and pointer automation"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"

[Registry]
; Launch at sign-in is switched on/off in the app (Options -> Startup); always remove it on uninstall.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "{#AppName}"; Flags: uninsdeletevalue dontcreatekey

[Run]
; Start RDP Nexus as soon as it is installed.
Filename: "{app}\{#AppExe}"; Flags: nowait; Check: ShouldLaunch

[UninstallDelete]
; Log files are app-generated; user settings in %APPDATA%\RDP Nexus are kept.
Type: filesandordirs; Name: "{localappdata}\RDP Nexus\logs"

[Code]
procedure CloseRunningCopy();
var
  ResultCode: Integer;
begin
  // An older RDP Nexus that is still running would lock its files: close it without asking.
  Log('Closing a running copy of {#AppExe}, if any');
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/f /im {#AppExe}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Log(Format('taskkill finished (exit code %d)', [ResultCode]));
end;

function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  if not WizardSilent() then
  begin
    // Double-clicked: Inno Setup always stops on its "Ready to Install" page when every other page is
    // off, so run this same installer in silent mode instead (a progress bar only, no pages, no
    // questions), and start RDP Nexus at the end.  This copy then exits.
    if Exec(ExpandConstant('{srcexe}'), '/SILENT /SUPPRESSMSGBOXES /NORESTART /LAUNCH=1', '', SW_SHOW,
            ewNoWait, ResultCode) then
      Result := False;
  end;
end;

function ShouldLaunch(): Boolean;
begin
  // Start RDP Nexus after a double-click install; a scripted silent install (without /LAUNCH=1) does not.
  Result := (not WizardSilent()) or (ExpandConstant('{param:LAUNCH|0}') = '1');
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  CloseRunningCopy();
  Result := '';
end;

function InitializeUninstall(): Boolean;
begin
  CloseRunningCopy();
  Result := True;
end;
