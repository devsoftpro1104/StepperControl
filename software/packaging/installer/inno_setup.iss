; Inno Setup скрипт сборки Windows-инсталлятора.
[Setup]
AppName=Stepper Controller
AppVersion=0.1.0
DefaultDirName={autopf}\StepperController
DefaultGroupName=Stepper Controller
OutputBaseFilename=stepper_controller_setup
Compression=lzma2
SolidCompression=yes

[Files]
Source: "..\\dist\\controller_app\\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{group}\\Stepper Controller"; Filename: "{app}\\controller_app.exe"