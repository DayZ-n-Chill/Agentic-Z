# Reference: File Paths and File System API

Enforce Script exposes a limited file I/O API. Paths use special `$` root tokens rather than absolute OS paths.

---

## Path Root Tokens

| Token | Resolves to | Writable | Notes |
|---|---|---|---|
| `$profile:` | `<DayZServerDir>\profiles\<profileName>\` | Yes | Primary mod storage |
| `$saves:` | Same as `$profile:` in most builds | Yes | Use `$profile:` instead |
| `$game:` | DayZ installation directory | No | Read vanilla assets |
| `$missions:` | Mission directory | No | Read mission data |

```c
// Full path example
string configPath = "$profile:\\MyMod\\config.json";
```

---

## File Existence and Directory Management

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

```c
FileHandle fh = OpenFile(file, FileMode.WRITE);
if (fh != 0)
{
    FPrint(fh, "line 1\n");
    FPrint(fh, "line 2\n");
    CloseFile(fh);
}
```

---

## JSON Read/Write (Preferred for Structured Data)

The `JsonFileLoader<T>` utility is preferred over manual file I/O for structured config/data:

```c
// Save
JsonFileLoader<MyMod_Config>.JsonSaveFile("$profile:\\MyMod\\config.json", configObject);

// Load into existing object
MyMod_Config cfg = new MyMod_Config();
JsonFileLoader<MyMod_Config>.JsonLoadFile("$profile:\\MyMod\\config.json", cfg);
```

Rules:
- All serialized fields must be `public`
- Nested `ref` objects serialize recursively
- Extra keys in file are silently ignored (safe for forward-compatible formats)
- Missing keys keep object defaults (safe for backward-compatible formats)

---

## Deleting and Renaming

```c
// Delete a file (returns true on success)
bool ok = DeleteFile("$profile:\\MyMod\\old_data.json");

// Rename / move (no built-in rename — copy + delete)
// (no CopyFile either — use JsonFileLoader for structured data or manual FGets/FPrint)
```

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

| Constant | Meaning |
|---|---|
| `FileMode.READ` | Open existing file for reading |
| `FileMode.WRITE` | Create or overwrite for writing |
| `FileMode.APPEND` | Open for appending (create if missing) |
