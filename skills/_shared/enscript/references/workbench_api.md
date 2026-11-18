# Reference: the Workbench scripting API

The Enforce Script surface that extends Workbench itself: the `Workbench` entry points, the `ResourceManager` and `ScriptEditor` modules, plugin events, the progress dialog, `MetaFile`, `GeneratedResources`, and the `#ifdef WORKBENCH` guard. For tool authors writing Workbench plugins, not for game scripts.

Two shapes of this API exist, and they differ:

- **On `P:\` (checked).** One file, `P:\scripts\1_core\workbenchapi.c` (160 lines). `class Workbench` opens at `:6`, not `sealed` and with no `#ifdef WORKBENCH` line above it, and `GetModule` takes a string: `static proto native WBModuleDef GetModule(string type)` (`:8`). `SearchResources(string filter, func callback)` is at `:13` and `RunCmd(string command, bool wait = false)` at `:14`. `class WorkbenchPlugin : Managed` is at `:106` and `WorkbenchPluginAttribute` at `:137`.
- **In 1.30.164200 and later (not yet checked on `P:\`).** The API moved into a `1_core\workbenchapi\` folder of 13 files (`game_builds.md`). The rest of this file describes that shape, read from a newer script tree. Its file names and line numbers cannot be opened on the older `P:\` extraction.

Open the Workbench API files of the build you target before using a signature from either list.

## The guard (newer shape)

`Workbench` and the module, dialog, metafile, generated resources, build context and attribute classes sit inside `#ifdef WORKBENCH` (`workbenchapi\workbench.c:1` to `:63`, `workbenchapi.c:6-93`). `WorkbenchPlugin` (`plugins\workbenchplugin.c:2`) has no guard. So: keep the plugin class unguarded if the file must also compile in game modules, and wrap every call into `Workbench`, `ResourceManager`, `ScriptEditor`, `WBProgressDialog`, `MetaFile` or `GeneratedResources`, and every `[WorkbenchPluginAttribute]` or `WBModuleDef`, in `#ifdef WORKBENCH`. An unguarded call is a compile error in the game module, not a null at run time.

## `Workbench` entry points (newer shape)

`sealed class Workbench` with a private constructor; every entry point is `static proto` (`workbench.c:10-60`).

| Method | Signature |
|---|---|
| `GetModule` | `WBModuleDef GetModule(typename type)` |
| `OpenModule`, `CloseModule` | `bool OpenModule(typename type)`, `bool CloseModule(typename type)` |
| `Dialog` | `void Dialog(string caption, string text, string detailedText = string.Empty)` |
| `ScriptDialog` | `int ScriptDialog(string caption, string text, Class data)` |
| `SearchResources` | `bool SearchResources(string filter, func callback)` |
| `RunCmd` | `int RunCmd(string command, bool wait = false)` |
| `RunProcess` | `ProcessHandle RunProcess(string command)` |
| `KillProcess`, `FinishProcess` | `bool KillProcess(ProcessHandle handle)`, `void FinishProcess(ProcessHandle handle)` |
| `IsRunningProcess`, `WaitProcess` | `bool IsRunningProcess(ProcessHandle handle)`, `int WaitProcess(ProcessHandle handle, int timeout = -1)` |
| `GetCwd`, `GetUserName`, `GetExecutableFilePath` | each `void (out string)` |
| `GetAbsolutePath` | `bool GetAbsolutePath(string relativePath, out string absPath, bool mustExist = true)` |
| `JumpToScriptSymbol`, `OpenResource` | `bool (string)` |
| `GetResourceName` | `ResourceName GetResourceName(string path)` |
| `GetCurrentGameProjectFile`, `GetGameProjectSettings` | `string ()`, `BaseContainer ()` |
| `GenerateGloballyUniqueID64`, `GetPackedUtcTime`, `Exit` | `string ()`, `DateTimeUtcAsInt ()`, `void (int exitCode)` |
| `GetWBScriptModule`, `GetWBGameScriptModule` | `ref ScriptModule ()` |

- `ProcessHandle` is `typedef int[]`. Pair every `RunProcess` with exactly one `KillProcess` (kills and closes) or `FinishProcess` (closes without killing).
- `GetAbsolutePath` defaults `mustExist` to `true`; pass `false` for a path that does not exist yet.
- `SearchResources` types its callback only as `func`. The vanilla tools pass `void(string file)`, also on `P:\`: `void Resave(string file)` at `P:\scripts\editor\workbench\resavetool.c:8`, passed at `:20` and `:33`, and `void CheckTextIDs(string file)` at `P:\scripts\editor\workbench\checkloctool.c:27`, passed at `:43`.

## Modules (newer shape)

`Workbench.GetModule(ResourceManager)` returns a `WBModuleDef` to cast. `WBModuleDef` (`modules\wbmoduledef.c:4-13`) has `SetOpenedResource`, `GetContainer`, `GetNumContainers`, `Save`, `GetCmdLine`, `Close`, `ExecuteAction` and `GetPlugin(typename)`.

`ResourceManager : WBModuleDef` (`modules\resourcemanager.c:6-38`), all `proto external`:

| Method | Signature |
|---|---|
| `GetMetaFile` | `MetaFile GetMetaFile(string absFilePath)` |
| `RegisterResourceFile` | `bool RegisterResourceFile(string absFilePath, bool bBuildRuntimeResource)` |
| `RebuildResourceFile` | `void RebuildResourceFile(string filePath, string configuration, bool selectFiles)` |
| `RebuildResourceFiles` | `void RebuildResourceFiles(notnull array<string> filePaths, string configuration)` |
| `WaitForFile` | `bool WaitForFile(string filePath, int maxTimeMs = 1000)`: false on timeout |

`ScriptEditor : WBModuleDef` (`modules\scripteditor.c:6-16`): `GetCurrentFile(out string)`, `GetCurrentLine()`, `GetLinesCount()`, `GetLineText(out string, int line = -1)`, `SetLineText`, `InsertLine`, `RemoveLine`. `line = -1` means the current line.

## Plugins (newer shape)

A plugin extends `WorkbenchPlugin` and overrides its events; Workbench creates it (private constructor) and calls them. `WorkbenchPlugin` events (`plugins\workbenchplugin.c:7-10`): `Run()`, `RunCommandline()`, `Configure()`, `OnResourceContextMenu(notnull array<ResourceName> resources)`.

`ResourceManagerPlugin : WorkbenchPlugin` (`plugins\resourcemanagerplugin.c:14-23`, inside the guard) has the events `OnRegisterResource`, `OnBuildResource` (returns a `BuildResourceContext`), `OnRenameResource`, `OnGetMaterialGenerateDir`, `OnGetMaterialClassName` and `OnMaterialCreated`. There is no rebuild event: rebuilding is a `ResourceManager` call. Return the `BuildResourceContext` from `OnBuildResource` and let Workbench poll its only member, `event bool IsWorking()` (`buildresourcecontext.c:5`); do not block inside the event.

## Progress, `MetaFile`, `GeneratedResources` (newer shape)

- `WBProgressDialog(string title, WBModuleDef parentWindow)` with `SetProgress(float)`, a fraction from 0.0 to 1.0, `SetMainTitle` and `SetActionTitle` (`wbprogressdialog.c:33-51`).
- `MetaFile` is both `typedef int[] MetaFile` and `sealed class MetaFile: BaseContainer` (`metafile.c:3-4`), with `GetResourceID()`, `GetSourceFilePath()` and `Save()`. `OnRegisterResource` hands the meta file over as a plain `BaseContainer`; use `ResourceManager.GetMetaFile` (or a cast) for the typed calls.
- `GeneratedResources` has one method, `bool RegisterResource(string absPath, out ResourceName resourceName)` (`generatedresources.c:16`). A plugin registers each file it generates and reads the assigned name from the `out` argument.
