# Workbench Enforce scripting API

Covers the Enforce Script surface that extends Workbench itself: the `Workbench` entry points, the `ResourceManager` and `ScriptEditor` modules, plugin events, the progress dialog, `MetaFile` and `GeneratedResources`, and the `#ifdef WORKBENCH` guard around them.

Status: source reading of build `119356`. Not yet checked on `P:\`: the `P:\scripts` tree this repo checks against has no `1_core\workbenchapi\` folder, so the `path:line` citations in the body cannot be opened there. What `P:\` does hold is listed under "What `P:\` holds" at the end, and it differs from this note.

Workbench scripting extends the editor itself: it opens modules, runs external tools, registers and rebuilds resources, and reacts to resource events. This note maps that Enforce surface for tool authors who extend Workbench. It is not a gameplay tutorial and does not cover the Python tools under `scripts/tools/` or the language rules in `enforce-script-reference`. Everything below is source-verified against build `119356` (`scripts/1_core/workbenchapi/` and `scripts/1_core/workbenchapi.c`). No runtime behaviour is claimed; a `proto` declaration proves the signature exists, not that a given build links a native behind it. No vanilla code is copied.

## The guard boundary

`Workbench` and the module classes exist only in Workbench builds: `scripts/1_core/workbenchapi/workbench.c:1` opens `#ifdef WORKBENCH` (closed at `workbench.c:63`), and the same guard wraps the module, dialog, metafile, generated-resources, build-context and attribute files (`scripts/1_core/workbenchapi.c:6-93`). `WorkbenchPlugin` is the exception: `plugins/workbenchplugin.c:2` declares `class WorkbenchPlugin : Managed` with no guard, while `plugins/resourcemanagerplugin.c:7` sits inside the guard. A game-side script can name `WorkbenchPlugin`, but `Workbench.GetModule` and every module method below vanish outside a Workbench build. Recipe: keep the plugin class unguarded if the file must compile in game modules, and wrap every call into `Workbench`, `ResourceManager`, `ScriptEditor`, `WBProgressDialog`, `MetaFile` or `GeneratedResources`, and every use of `[WorkbenchPluginAttribute]` or `WBModuleDef`, in `#ifdef WORKBENCH`. An unguarded call is a compile error in the game module, not a runtime null.

## Workbench entry points

`Workbench` is `sealed class Workbench` with a private constructor (`workbench.c:5-8`); every entry point is `static proto`. The exact signatures in `scripts/1_core/workbenchapi/workbench.c:10-60` are:

| Method | Exact signature |
|---|---|
| `GetModule` | `static proto WBModuleDef GetModule(typename type)` |
| `OpenModule` | `static proto bool OpenModule(typename type)` |
| `CloseModule` | `static proto bool CloseModule(typename type)` |
| `Dialog` | `static proto void Dialog(string caption, string text, string detailedText = string.Empty)` |
| `ScriptDialog` | `static proto int ScriptDialog(string caption, string text, Class data)` |
| `SearchResources` | `static proto bool SearchResources(string filter, func callback)` |
| `RunCmd` | `static proto int RunCmd(string command, bool wait = false)` |
| `JumpToScriptSymbol` | `static proto bool JumpToScriptSymbol(string symbol)` |
| `RunProcess` | `static proto ProcessHandle RunProcess(string command)` |
| `KillProcess` | `static proto bool KillProcess(ProcessHandle handle)` |
| `IsRunningProcess` | `static proto bool IsRunningProcess(ProcessHandle handle)` |
| `WaitProcess` | `static proto int WaitProcess(ProcessHandle handle, int timeout = -1)` |
| `FinishProcess` | `static proto void FinishProcess(ProcessHandle handle)` |
| `GetCwd` | `static proto void GetCwd(out string currentDir)` |
| `GetUserName` | `static proto void GetUserName(out string userName)` |
| `GetAbsolutePath` | `static proto bool GetAbsolutePath(string relativePath, out string absPath, bool mustExist = true)` |
| `GetExecutableFilePath` | `static proto void GetExecutableFilePath(out string filePath)` |
| `GetCurrentGameProjectFile` | `static proto string GetCurrentGameProjectFile()` |
| `GetGameProjectSettings` | `static proto BaseContainer GetGameProjectSettings()` |
| `GenerateGloballyUniqueID64` | `static proto string GenerateGloballyUniqueID64()` |
| `Exit` | `static proto void Exit(int exitCode)` |
| `GetPackedUtcTime` | `static proto DateTimeUtcAsInt GetPackedUtcTime()` |
| `GetResourceName` | `static proto ResourceName GetResourceName(string path)` |
| `OpenResource` | `static proto bool OpenResource(string filename)` |
| `GetWBScriptModule` | `static proto ref ScriptModule GetWBScriptModule()` |
| `GetWBGameScriptModule` | `static proto ref ScriptModule GetWBGameScriptModule()` |

`ProcessHandle` is `typedef int[] ProcessHandle` (`workbench.c:3`). `RunCmd` runs a command line, optionally blocks (`wait = false` by default) and returns an `int`. `RunProcess` starts a process and returns a `ProcessHandle` immediately; lifetime is then explicit: `IsRunningProcess` polls, `WaitProcess` blocks with a millisecond timeout (`-1` by default), `KillProcess` kills and closes the handle, and `FinishProcess` closes the handle without killing. Pair every `RunProcess` with exactly one `KillProcess` or `FinishProcess`. The `out` methods write through the argument: `GetCwd`, `GetUserName` and `GetExecutableFilePath` take only an `out string`, while `GetAbsolutePath` returns `bool` and also writes `out string absPath`; `mustExist` defaults to `true`, so a path that need not exist yet requires an explicit `false`. `SearchResources(string filter, func callback)` declares its callback only as bare `func` in `workbench.c:15`, but the vanilla Workbench plugins pass `void(string file)` callbacks (`editor/workbench/resavetool.c:8,20,33` and `editor/workbench/checkloctool.c:27,43`), so the parameter shape is visible in source even though the header does not type it.

## Modules

Modules are reached by type: `Workbench.GetModule(ResourceManager)` returns the `WBModuleDef`, which the caller casts to the module class. `WBModuleDef` is `sealed class WBModuleDef` (`modules/wbmoduledef.c:4`) with `SetOpenedResource`, `GetContainer`, `GetNumContainers`, `Save`, `GetCmdLine`, `Close`, `ExecuteAction` and `GetPlugin(typename pluginType)` (`modules/wbmoduledef.c:6-13`). `ResourceManager` is `sealed class ResourceManager: WBModuleDef` (`modules/resourcemanager.c:4`). Its exact methods in `scripts/1_core/workbenchapi/modules/resourcemanager.c:6-38` are:

| Method | Exact signature |
|---|---|
| `GetMetaFile` | `proto external MetaFile GetMetaFile(string absFilePath)` |
| `RegisterResourceFile` | `proto external bool RegisterResourceFile(string absFilePath, bool bBuildRuntimeResource)` |
| `RebuildResourceFile` | `proto external void RebuildResourceFile(string filePath, string configuration, bool selectFiles)` |
| `RebuildResourceFiles` | `proto external void RebuildResourceFiles(notnull array<string> filePaths, string configuration)` |
| `WaitForFile` | `proto external bool WaitForFile(string filePath, int maxTimeMs = 1000)` |

Note the singular/plural split: `RebuildResourceFile` takes one path plus a `selectFiles` flag, while `RebuildResourceFiles` takes a `notnull array<string>` and no flag. `WaitForFile` waits for the Resource Database to acknowledge a file and returns `false` on timeout (`1000` ms by default). `ScriptEditor` is `sealed class ScriptEditor: WBModuleDef` (`modules/scripteditor.c:4`) with, in `modules/scripteditor.c:6-16`: `GetCurrentFile(out string filename)`, `GetCurrentLine()`, `GetLinesCount()`, `GetLineText(out string text, int line = -1)`, `SetLineText(string text, int line = -1)`, `InsertLine(string text, int line = -1)` and `RemoveLine(int line = -1)`, all `proto external` with the return types `bool`, `int`, `int`, `bool`, `void`, `void`, `void`. In `ScriptEditor`, `line = -1` means the current line.

## Plugins

A plugin extends `WorkbenchPlugin` and overrides `event` methods; the engine calls them, the plugin does not invoke them itself. `WorkbenchPlugin` events in `scripts/1_core/workbenchapi/plugins/workbenchplugin.c:7-10` are:

| Event | Exact signature |
|---|---|
| `Run` | `event void Run()` |
| `RunCommandline` | `event void RunCommandline()` |
| `Configure` | `event void Configure()` |
| `OnResourceContextMenu` | `event void OnResourceContextMenu(notnull array<ResourceName> resources)` |

`WorkbenchPlugin` has a private constructor and destructor (`plugins/workbenchplugin.c:4-5`); plugins are instantiated by Workbench, not by `new` from tool code. The attribute that names a tool in the Script Tools menu is `WorkbenchPluginAttribute` in `scripts/1_core/workbenchapi.c:63`, inside the guard that opens at `:6` and closes at `:93` (`scripts/1_core/workbenchapi.c:63-86`). `ResourceManagerPlugin` is `class ResourceManagerPlugin: WorkbenchPlugin` (`plugins/resourcemanagerplugin.c:14`), inside `#ifdef WORKBENCH`. Its events in `plugins/resourcemanagerplugin.c:16-23` are `OnRegisterResource(string absFileName, BaseContainer metaFile)`, `OnBuildResource(string absSrcFileName, string absDestFileName, BaseContainer metaFile, BaseContainer configuration, GeneratedResources generatedResources)` returning `BuildResourceContext`, `OnRenameResource(string absFileNameOld, string absFileNameNew, BaseContainer metaFile)`, `OnGetMaterialGenerateDir(string absModelPath)` returning `string`, `OnGetMaterialClassName(string absMaterialPath, GeneratedResources generatedResources)` returning `string`, and `OnMaterialCreated(string absMaterialPath, BaseContainer materialSrc, GeneratedResources generatedResources)`, all `event`. There is no `OnRebuildResource` event in this build; rebuild is a `ResourceManager` method call, while build is the plugin event. `OnBuildResource` is the only event here that returns a value: a `BuildResourceContext`, whose whole surface is `event bool IsWorking()` (`buildresourcecontext.c:5`). Return the context from the event and let Workbench poll `IsWorking()`; do not block inside the event.

## Progress, MetaFile, GeneratedResources

`WBProgressDialog` is `sealed class WBProgressDialog: Managed` (`wbprogressdialog.c:33`). Its exact surface in `scripts/1_core/workbenchapi/wbprogressdialog.c:35-51` is:

| Member | Exact signature |
|---|---|
| Constructor | `void WBProgressDialog(string title, WBModuleDef parentWindow)` |
| `SetProgress` | `proto external void SetProgress(float progress)` |
| `SetMainTitle` | `proto external void SetMainTitle(string text)` |
| `SetActionTitle` | `proto external void SetActionTitle(string text)` |

`SetProgress` takes a fraction in `[0.0, 1.0]`, not a percentage, and the constructor takes the owning module window. `MetaFile` carries a name collision: `metafile.c:3` declares `typedef int[] MetaFile` and `metafile.c:4` declares `sealed class MetaFile: BaseContainer`. The class surface in `scripts/1_core/workbenchapi/metafile.c:4-9` is:

| Member | Exact signature |
|---|---|
| `GetResourceID` | `proto external ResourceName GetResourceID()` |
| `GetSourceFilePath` | `proto external string GetSourceFilePath()` |
| `Save` | `proto external void Save()` |

`ResourceManager.GetMetaFile` returns this `MetaFile` class, while `ResourceManagerPlugin.OnRegisterResource` receives the meta file as a plain `BaseContainer`; the typed API (`GetResourceID`, `GetSourceFilePath`, `Save`) needs the `GetMetaFile` result (or a cast), not the event argument as declared. `GeneratedResources` is `sealed class GeneratedResources: Managed` (`generatedresources.c:14`). Its only method, in `scripts/1_core/workbenchapi/generatedresources.c:16`, is:

| Member | Exact signature |
|---|---|
| `RegisterResource` | `proto bool RegisterResource(string absPath, out ResourceName resourceName)` |

A plugin receives a `GeneratedResources` instance through `OnBuildResource`, `OnGetMaterialClassName` and `OnMaterialCreated`; it registers each file it generates by absolute path and reads the assigned `ResourceName` from the `out` argument.

## What this changes

A tool author now has the whole extension recipe in one place: subclass `WorkbenchPlugin` (unguarded), guard every `Workbench` call, `[WorkbenchPluginAttribute]` and `WBModuleDef` with `#ifdef WORKBENCH`, get the module with `Workbench.GetModule`, drive files through `ResourceManager`, report long work with `WBProgressDialog`, and return a `BuildResourceContext` from `OnBuildResource` instead of blocking. The traps are the three the map makes visible. First, the guard: `WorkbenchPlugin` compiles in game modules and `Workbench` does not, so a plugin file that calls `Workbench.GetModule` or uses `[WorkbenchPluginAttribute]`/`WBModuleDef` unguarded breaks the game build. Second, `SearchResources` declares the callback as bare `func`; the vanilla plugins pass `void(string file)`, so the parameter shape is visible in source even though the header does not type it. Third, `MetaFile` is both a `typedef int[]` and a sealed class, and the plugin events hand it over as `BaseContainer`; reaching for `GetResourceID` on the event argument without `ResourceManager.GetMetaFile` (or a cast) does not type-check.

## How to reproduce

Read the thirteen source files cited below, in build `119356`:

- `workbench.c` — entry points and the guard.
- `modules/wbmoduledef.c` — `WBModuleDef`.
- `scripts/1_core/workbenchapi.c` — `WorkbenchPluginAttribute`.
- `wbprogressdialog.c` — progress dialog.
- `metafile.c` — `MetaFile` class and typedef.
- `generatedresources.c` — `GeneratedResources`.
- `buildresourcecontext.c` — `BuildResourceContext`.
- `modules/resourcemanager.c` — `ResourceManager`.
- `modules/scripteditor.c` — `ScriptEditor`.
- `plugins/workbenchplugin.c` — `WorkbenchPlugin`.
- `plugins/resourcemanagerplugin.c` — `ResourceManagerPlugin`.
- `editor/workbench/resavetool.c` — `SearchResources` callback `void(string file)`.
- `editor/workbench/checkloctool.c` — second `SearchResources` callback example.

Each table above names its file and line range.

## Limits

- Build `119356` only.
- Later Workbench builds may add or rename entry points.
- Source-verified only: no Workbench instance was run.
- Linkage of each `proto` is therefore unmeasured.
- The `SearchResources` callback parameter shape is visible in the vanilla plugins as `void(string file)`; the engine's exact invocation and return convention are unmeasured.
- Runtime values beyond declared defaults are unmeasured.
- That includes exit codes and observed timeouts.
- The API exists only where `WORKBENCH` is defined.
- Nothing here is callable from a retail game module.
- No vanilla code is copied.
- Signatures are cited by `path:line`.
- The prose is paraphrase.

## What `P:\` holds

Opened on 2026-11-17. The `P:\scripts` tree has the Workbench API as one file, `P:\scripts\1_core\workbenchapi.c` (160 lines), with an older shape than the body of this note describes:

- `class Workbench` opens at `P:\scripts\1_core\workbenchapi.c:6`, not `sealed` and with no `#ifdef WORKBENCH` line above it.
- `GetModule` takes a string there, not a `typename`: `static proto native WBModuleDef GetModule(string type)` at `P:\scripts\1_core\workbenchapi.c:8`.
- `SearchResources(string filter, func callback)` is declared at `P:\scripts\1_core\workbenchapi.c:13` and `RunCmd(string command, bool wait = false)` at `P:\scripts\1_core\workbenchapi.c:14`; both agree with the note.
- `class WorkbenchPlugin : Managed` is at `P:\scripts\1_core\workbenchapi.c:106` and `WorkbenchPluginAttribute` at `P:\scripts\1_core\workbenchapi.c:137`.
- The two callback examples agree with the note: `void Resave(string file)` at `P:\scripts\editor\workbench\resavetool.c:8`, passed to `SearchResources` at `:20` and `:33`, and `void CheckTextIDs(string file)` at `P:\scripts\editor\workbench\checkloctool.c:27`, passed at `:43`.

So before using a signature from the body, open the Workbench API files of the build you target.
