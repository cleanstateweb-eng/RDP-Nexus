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
#define SingleInstanceMutex "RDPNexus.SingleInstance"

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
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Check: not IsUpdateOnly

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"; Comment: "RDP-only keyboard and pointer automation"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"

[Registry]
; Launch at sign-in is switched on/off in the app (Options -> Startup); always remove it on uninstall.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "{#AppName}"; Flags: uninsdeletevalue dontcreatekey

[Run]
; A newer release was downloaded during this install: hand over to it (it starts RDP Nexus itself).
Filename: "{code:NewestSetupPath}"; Parameters: "/SILENT /SUPPRESSMSGBOXES /NORESTART /LAUNCH=1 /NOUPDATE=1"; StatusMsg: "Installing the newest version of {#AppName}..."; Flags: waituntilterminated; Check: HaveNewestSetup
; Otherwise start RDP Nexus as soon as it is installed.
Filename: "{app}\{#AppExe}"; Flags: nowait; Check: ShouldLaunch and not HaveNewestSetup

[UninstallDelete]
; Log files are app-generated; user settings in %APPDATA%\RDP Nexus are kept.
Type: filesandordirs; Name: "{localappdata}\RDP Nexus\logs"

[Code]
// "Always install the newest version":
//  * As the installation starts, the installer looks up the newest release on GitHub
//    (SHA256SUMS.txt of the latest release, a few hundred bytes).  If that is newer, it downloads the
//    newest installer, verifies its SHA-256, installs its own files as a fallback, then runs the newest
//    installer silently.  Offline: you keep what it contains.
//  * An installer never downgrades: if a newer version is already installed, it does not copy its own
//    (older) files; it still hands over to an even newer release if GitHub has one, and otherwise
//    leaves everything as it is and makes sure RDP Nexus is running.
const
  LatestURL = '{#AppURL}/releases/latest/download/';
  UninstallKey = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\{8F3C2B71-5D7A-4E8B-9C21-6A4D3E2F1B90}_is1';

var
  NewestSetup: String;      // a downloaded, verified newer installer ('' = none)
  UpdateOnly: Boolean;      // a newer version than this installer is already installed
  InstalledVer, InstalledFolder: String;

procedure CloseRunningCopy();
var
  ResultCode: Integer;
begin
  // An older RDP Nexus that is still running would lock its files: close it without asking.
  Log('Closing a running copy of {#AppExe}, if any');
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/f /im {#AppExe}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Log(Format('taskkill finished (exit code %d)', [ResultCode]));
end;


function NextNumber(var S: String): Integer;
var
  P: Integer;
begin
  P := Pos('.', S);
  if P = 0 then begin
    Result := StrToIntDef(Trim(S), 0);
    S := '';
  end else begin
    Result := StrToIntDef(Trim(Copy(S, 1, P - 1)), 0);
    Delete(S, 1, P);
  end;
end;

// -1 if X is older than Y, 0 if equal, 1 if newer ("1.0.10" is newer than "1.0.9").
function CompareVersions(X, Y: String): Integer;
var
  I, A, B: Integer;
begin
  Result := 0;
  for I := 1 to 4 do begin
    A := NextNumber(X);
    B := NextNumber(Y);
    if A <> B then begin
      if A > B then Result := 1 else Result := -1;
      Exit;
    end;
  end;
end;

// Version and folder of the RDP Nexus that is installed now ('' if none, or its program is missing).
function InstalledVersion(var Folder: String): String;
var
  Version: String;
begin
  Result := '';
  Folder := '';
  if RegQueryStringValue(HKCU, UninstallKey, 'DisplayVersion', Version) and
     RegQueryStringValue(HKCU, UninstallKey, 'InstallLocation', Folder) then begin
    Folder := AddBackslash(Folder);
    if FileExists(Folder + '{#AppExe}') then
      Result := Version;
  end;
end;

// The newest release on GitHub: its version and the SHA-256 of its RDPNexus-setup.exe.
function FindNewestRelease(var Version, Sha: String): Boolean;
var
  Lines: TArrayOfString;
  I, P, Q: Integer;
  Line, Name: String;
begin
  Result := False;
  Version := '';
  Sha := '';
  try
    DownloadTemporaryFile(LatestURL + 'SHA256SUMS.txt', 'newest-SHA256SUMS.txt', '', nil);
  except
    Log('Could not check for a newer version: ' + GetExceptionMessage);
    Exit;
  end;
  if not LoadStringsFromFile(ExpandConstant('{tmp}\newest-SHA256SUMS.txt'), Lines) then
    Exit;
  for I := 0 to GetArrayLength(Lines) - 1 do begin
    Line := Trim(Lines[I]);
    P := Pos(' ', Line);
    if P = 0 then
      Continue;
    Name := Trim(Copy(Line, P + 1, Length(Line)));
    if (Length(Name) > 0) and (Name[1] = '*') then
      Delete(Name, 1, 1);
    Q := Pos('-setup.exe', Name);
    if Name = 'RDPNexus-setup.exe' then
      Sha := LowerCase(Copy(Line, 1, P - 1))
    else if (Pos('RDPNexus-', Name) = 1) and (Q > 10) then
      Version := Copy(Name, 10, Q - 10);
  end;
  Result := (Version <> '') and (Length(Sha) = 64);
  Log(Format('Newest release on GitHub: %s (this installer: {#AppVersion})', [Version]));
end;

function ShouldLaunch(): Boolean;
begin
  // Start RDP Nexus after a double-click install; a scripted silent install (without /LAUNCH=1) does not.
  Result := (not WizardSilent()) or (ExpandConstant('{param:LAUNCH|0}') = '1');
end;

function OnNewestDownloadProgress(const Url, FileName: String; const Progress, ProgressMax: Int64): Boolean;
begin
  if ProgressMax > 0 then begin
    WizardForm.ProgressGauge.Max := 1000;
    WizardForm.ProgressGauge.Position := Integer(Progress * 1000 div ProgressMax);
    WizardForm.FilenameLabel.Caption := Format('%d of %d KB', [Integer(Progress div 1024), Integer(ProgressMax div 1024)]);
  end;
  Result := True;
end;

procedure StartInstalledCopy();
var
  ResultCode: Integer;
begin
  if ShouldLaunch() and not CheckForMutexes('{#SingleInstanceMutex}') then
    Exec(InstalledFolder + '{#AppExe}', '', '', SW_SHOW, ewNoWait, ResultCode);
end;

procedure FetchNewerRelease();
var
  Version, Sha, Have: String;
begin
  WizardForm.StatusLabel.Caption := 'Checking for a newer version of {#AppName}...';
  if UpdateOnly then Have := InstalledVer else Have := '{#AppVersion}';
  if FindNewestRelease(Version, Sha) and (CompareVersions(Version, Have) > 0) then begin
    WizardForm.StatusLabel.Caption := Format('Downloading {#AppName} %s, the newest version...', [Version]);
    try
      DownloadTemporaryFile(LatestURL + 'RDPNexus-setup.exe', 'RDPNexus-newest-setup.exe', Sha,
                            @OnNewestDownloadProgress);
      NewestSetup := ExpandConstant('{tmp}\RDPNexus-newest-setup.exe');
      Log('Downloaded and verified the newest version ' + Version);
    except
      Log('Could not download the newest version (keeping ' + Have + '): ' + GetExceptionMessage);
    end;
  end;
  if UpdateOnly and (NewestSetup = '') then begin
    // Already newer than this installer and nothing newer online: change nothing.
    Log(Format('%s is already installed, newer than this installer ({#AppVersion}); not downgrading', [InstalledVer]));
    StartInstalledCopy();
    Abort;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  // At the start of the installation, before any file is copied, so the hand-over in [Run] is ready.
  if CurStep <> ssInstall then
    Exit;
  if ExpandConstant('{param:NOUPDATE|0}') <> '1' then
    FetchNewerRelease();  // aborts (changing nothing) if there is nothing to install
  CloseRunningCopy();     // only now, so a running RDP Nexus is left alone when nothing changes
end;

function IsUpdateOnly(): Boolean;
begin
  Result := UpdateOnly;
end;

function HaveNewestSetup(): Boolean;
begin
  Result := NewestSetup <> '';
end;

function NewestSetupPath(Param: String): String;
begin
  Result := NewestSetup;
end;

function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  // Never downgrade: with a newer version installed, only a still newer release may be installed.
  InstalledVer := InstalledVersion(InstalledFolder);
  UpdateOnly := (InstalledVer <> '') and (CompareVersions(InstalledVer, '{#AppVersion}') > 0);
  if UpdateOnly and (ExpandConstant('{param:NOUPDATE|0}') = '1') then begin
    Log(Format('%s is already installed, newer than this installer ({#AppVersion}); not downgrading', [InstalledVer]));
    StartInstalledCopy();
    Result := False;
    Exit;
  end;
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

function InitializeUninstall(): Boolean;
begin
  CloseRunningCopy();
  Result := True;
end;
