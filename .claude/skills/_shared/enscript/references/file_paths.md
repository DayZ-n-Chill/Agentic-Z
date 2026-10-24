# Reference: File Paths and File System API

Enforce Script exposes a limited file I/O API. Paths use special `$` root tokens rather than absolute OS paths. The file functions are declared in `P:\scripts\1_core\proto\ensystem.c` (line numbers below are in that file unless another is named).

---

## Path Root Tokens

| Token | Resolves to | Writable | Vanilla use |
|---|---|---|---|
| `$profile:` | The `-profiles=` folder of the running server or client | Yes | `OpenFile("$profile:testiik.txt", FileMode.WRITE)` (`ensystem.c:406`) |
| `$saves:` | The saves folder | Yes | `FILE_ROOT = "$saves:"` (`P:\scripts\4_world\plugins\pluginbase\pluginfilehandler\pluginconfighandler\pluginconfigscene.c:3`) |
| `$mission:` | The loaded mission folder | No | `string.Format("$mission:%1", m_ConfigFilePath)` (`P:\scripts\3_game\cfgbunkerbroadcasthandler.c:23`) |

Note the spelling: it is `$mission:` (singular). `$missions:` is not a vanilla token, so a path built with it fails. `DeleteFile` and the target of `CopyFile` work only on `$profile:` and `$saves:` (`ensystem.c:527` and `:530`). A `$game:` token is not used anywhere in the vanilla scripts, so it is not listed here.

```c
// Full path example
string configPath = "$profile:\\MyMod\\config.json";
```

---

## File Existence and Directory Management

`FileExist(string name)` (`:397`) and `MakeDirectory(string name)` (`:525`):

```c
string folder = "$profile:\\MyMod\\";
string file   = folder + "data.json";

// Check existence
if (!FileExist(folder))
    MakeDirectory(folder);   // create if missing

if (FileExist(file))
    Print("File was found");
```

---

## Reading a File (line by line)

`OpenFile(string name, FileMode mode)` (`:417`), `FGets(FileHandle file, string var)` (`:501`), `CloseFile(FileHandle file)` (`:443`). `ReadFile(FileHandle file, void param_array, int length)` (`:425`) reads a whole block instead.

```c
FileHandle fh = OpenFile(file, FileMode.READ);
if (fh != 0)
{
    string line;
    while (FGets(fh, line) >= 0)
    {
        Print("Line: " + line);
    }
    CloseFile(fh);
}
```

---

## Writing a File

`FPrint(FileHandle file, void var)` (`:462`) writes the value; `FPrintln` (`:481`) adds a line break.

```c
FileHandle fh = OpenFile(file, FileMode.WRITE);
if (fh != 0)
{
    FPrint(fh, "line 1\n");
    FPrintln(fh, "line 2");
    CloseFile(fh);
}
```

---

## JSON Read/Write (Preferred for Structured Data)

The `JsonFileLoader<T>` utility is preferred over manual file I/O for structured config/data. Use `LoadFile` and `SaveFile`, which return `bool` and an error message (`P:\scripts\3_game\tools\jsonfileloader.c:7` and `:42`); vanilla marks the older `JsonLoadFile` and `JsonSaveFile` "use JsonFileLoader::LoadFile instead" (`jsonfileloader.c:104-105`).

```c
string err;

// Save
if (!JsonFileLoader<MyMod_Config>.SaveFile("$profile:\\MyMod\\config.json", configObject, err))
    Print("[MyMod] save failed: " + err);

// Load into existing object
MyMod_Config cfg = new MyMod_Config();
if (!JsonFileLoader<MyMod_Config>.LoadFile("$profile:\\MyMod\\config.json", cfg, err))
    Print("[MyMod] load failed: " + err);
```

Rules:
- All serialized fields must be `public`
- Nested `ref` objects serialize recursively
- Extra keys in file are silently ignored (safe for forward-compatible formats)
- Missing keys keep object defaults (safe for backward-compatible formats)

---

## Deleting, Copying and Listing

```c
// Delete a file (returns true on success; $profile: and $saves: only)
bool ok = DeleteFile("$profile:\\MyMod\\old_data.json");

// Copy a file (the target must be in $profile: or $saves:)
CopyFile("$mission:mymod_defaults.json", "$profile:\\MyMod\\config.json");

// Rename or move = CopyFile, then DeleteFile on the source
```

`DeleteFile` is at `:528` and `CopyFile(string sourceName, string destName)` at `:531`. `FindFile`, `FindNextFile` and `CloseFindFile` (`:520-522`) list the files that match a pattern.

---

## Workbench / Packing Paths

| Context | Path |
|---|---|
| Script source files | `Scripts/<layer>/<YourFile>.c` |
| Config (server) | `<ServerDir>\mpmissions\<mission>\cfggameplay.json` |
| Economy | `<ServerDir>\mpmissions\<mission>\db\*.xml` |
| Mod PBO output | `<DayZDir>\@MyMod\addons\MyMod.pbo` |
| Workbench project | `<DayZDir>\Projects\MyMod\` |
| Profile root | `<ServerDir>\profiles\<profileName>\` |

---

## File Mode Constants

`enum FileMode { READ, WRITE, APPEND }` (`ensystem.c:382`).

| Constant | Meaning |
|---|---|
| `FileMode.READ` | Open existing file for reading |
| `FileMode.WRITE` | Create or overwrite for writing |
| `FileMode.APPEND` | Open for appending (create if missing) |
