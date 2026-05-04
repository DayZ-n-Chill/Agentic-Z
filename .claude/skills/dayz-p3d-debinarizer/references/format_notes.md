# DayZ ODOL Format Reference

## Table of Contents
1. [DayZ vs Arma 3 Differences](#1-dayz-vs-arma-3-differences)
2. [Compression System](#2-compression-system)
3. [EmbeddedMaterial v20 Format](#3-embeddedmaterial-v20-format)
4. [ODOL File Structure](#4-odol-file-structure)
5. [LOD Structure](#5-lod-structure)
6. [Fire Packer Container Format](#6-fire-packer-container-format)
7. [Conversion Logic (ODOL → MLOD)](#7-conversion-logic)

---

## 1. DayZ vs Arma 3 Differences

### 1.1 ModelInfo Extra Fields

DayZ ODOL v54 has three undocumented fields in ModelInfo that Arma 3 does not:

**Field 1: `allowAnimation` (bool, 1 byte)**
- Location: after `canBeOccluded`, before thermal profile data
- Present when: DayZ v54 (condition: `version >= 73 || isDayZ`)
- BisDLL offset impact: shifts all subsequent fields by +1 byte

**Field 2: `forceNotAlpha` as uint32 (4 bytes instead of 1)**
- Location: after thermal profile data
- Arma 3 reads as bool (1 byte); DayZ reads as uint32 (4 bytes)
- Impact: +3 bytes shift

**Field 3: `disableCover` (bool, 1 byte)**
- Location: before `animated` field
- Present when: DayZ v54 (same condition as allowAnimation)
- Impact: +1 byte shift

**Total shift from Arma 3**: 5 bytes additional in ModelInfo

### 1.2 hasAnims Byte

Arma 3 (v>=30) always has a `hasAnims` bool between ModelInfo and LOD addresses.
DayZ v54 behavior is inconsistent:
- Models with 0 skeleton bones: hasAnims byte is ABSENT
- Models with bones/animations: hasAnims byte is PRESENT (typically True)

**Detection heuristic (implemented in `ODOL._read`):**
```
1. Save position
2. Read 1 byte as hasAnims
3. If True:
   a. Peek next uint32 as n_animation_classes
   b. If n_classes < 10000 → valid, parse animations
   c. If n_classes >= 10000 → false positive, rewind
4. If False:
   a. Peek next uint32 as potential LOD address
   b. If > file_size → false positive, rewind
```

### 1.3 Material Version 20

DayZ uses material version 20, Arma 3 uses versions ≤ 11.
See Section 3 for full format specification.

### 1.4 BI LZO Variant

BI's LZO1X implementation differs from standard miniLZO in M4 match offset:
- **Standard LZO1X**: `m_pos = op - [(t&8)<<11] - [2-byte offset] - 16384`
- **BI variant**: `m_pos = op - [(t&8)<<11] - [2-byte offset]` (NO -16384)

This means standard python-lzo library CANNOT decompress BI's LZO data.
Our `lzo_decompress.py` implements the BI variant correctly.

---

## 2. Compression System

### 2.1 The 1024 Rule (v < 64)

For ODOL versions < 64, arrays are compressed only if `expected_size >= 1024` bytes.
Smaller arrays are stored raw (uncompressed).

### 2.2 Compression Flag (v >= 64)

For ODOL versions >= 64, each compressible block is preceded by a bool:
- True: data is compressed
- False: data is raw

**CRITICAL**: DayZ v54 is < 64, so it uses the 1024 rule, NOT compression flags.
Setting `use_compression_flag = True` for v54 will desynchronize ALL compressed reads.

### 2.3 Compressed Block Format

LZO compressed blocks have NO size prefix. The decompressor reads bytes from the
stream until it has produced `expected_size` output bytes. The decompressor returns
both the decompressed data and the count of input bytes consumed.

### 2.4 Condensed Arrays

Format: `count(u32) + defaultFill(bool) + data`
- If defaultFill=True: single value that fills the entire array
- If defaultFill=False: compressed array of `count` elements (subject to 1024 rule)

Used for: clip flags, point flags, UV data, normals.

---

## 3. EmbeddedMaterial v20 Format

### 3.1 Standard Fields (all versions)

```
materialName      asciiz
version           uint32        (= 20 for DayZ)
emissive          ColorP        (4 floats: RGBA)
ambient           ColorP
diffuse           ColorP
forcedDiffuse     ColorP
specular          ColorP
specularCopy      ColorP
specularPower     float
pixelShader       uint32        (enum: 0=PSNormal, 14=BasicAS, 23=Super, etc.)
```

### 3.2 DayZ Extended Fields (v >= 20)

After `pixelShader`, BEFORE `vertexShader`:

```
dayz_extended[25]  float[25]    (100 bytes of PBR extended material data)
```

These 25 floats encode additional PBR parameters. Known patterns observed:
- Float[0]: ~0.3 (roughness-like)
- Float[1]: ~0.99 (metalness-like) 
- Float[2-5]: RGBA color (may be specular2)
- Float[6]: specularPower2 (e.g. 30.0)
- Float[13]: 0xFFFFFFFF (NaN marker)
- Float[14-15]: 30.0, 45.0 (angle parameters?)
- Float[17]: 0xFFFFFFFF (NaN marker)
- Float[19]: 1.0

### 3.3 Post-Extended Fields

```
vertexShader      uint32        (DayZ may use values > 32, e.g. 102)
mainLight         uint32        
fogMode           uint32        (typically 3 = FogAlpha)
dayz_unknown      uint32        (v >= 20 only, typically 1)
surfaceFile       asciiz        (v >= 6, e.g. "dz\data\penetration\wood.bisurf")
nRenderFlags      uint32        (v >= 4)
renderFlags       uint32        (v >= 4)
nStages           uint32        (v > 6)
nTexGens          uint32        (v > 8)
```

### 3.4 Stage Textures

```
StageTexture[nStages]:
    filter        uint32        (v >= 5: 0=Point, 1=Linear, 2=Trilinear, 3=Anisotropic)
    texture       asciiz        (texture path or procedural: "#(argb,8,8,3)color(r,g,b,a,type)")
    stageId       uint32        (v >= 8)
    useWorldEnvMap bool          (v >= 11)
```

**Note**: First stage texture is a dummy entry (empty texture path, stageId=0).

### 3.5 Stage Transforms

```
StageTransform[nTexGens]:
    uvSource      uint32
    matrix        float[12]     (4x3 texture transform matrix, 48 bytes)
```

### 3.6 Stage TI (v >= 10)

One additional StageTexture after the transforms.

---

## 4. ODOL File Structure

```
ODOL {
    signature       char[4]       "ODOL"
    version         uint32        (54 for DayZ)
    nLods           uint32
    resolutions     float[nLods]  (LOD resolution values)
    ModelInfo       struct        (see odol_reader.py ODOL_ModelInfo)
    
    [DayZ: hasAnims detection - see Section 1.2]
    
    hasAnims        bool          (may be absent in DayZ)
    Animations      struct        (if hasAnims, see Animations.read)
    
    lodStartAddrs   uint32[nLods] (byte offsets to LOD data)
    lodEndAddrs     uint32[nLods]
    permanent       bool[nLods]   (True = LOD data at lodStartAddr)
    
    [For non-permanent LODs: LoadableLodInfo read sequentially]
    
    LOD[nLods]                    (at lodStartAddrs[i])
}
```

### 4.1 LOD Resolution Values

| Resolution | LOD Type |
|-----------|----------|
| 0.0 - 999.0 | Visual (value = view distance in meters) |
| ~1.0e13 | Geometry |
| ~1.0e15 | Memory |
| ~6.0e15 | View Geometry |
| ~7.0e15 | Fire Geometry |

---

## 5. LOD Structure

```
LOD {
    proxies[]              Proxy array (count-prefixed)
    subSkeletonsToSkeleton int32 array
    skeletonToSubSkeleton  int32 array of arrays
    vertexCountHint        uint32 (v >= 50)
    faceArea               float (v >= 51)
    orHints                int32
    andHints               int32
    bboxMin                Vector3P
    bboxMax                Vector3P
    bboxCenter             Vector3P
    bboxRadius             float
    textures[]             string array
    materials[]            EmbeddedMaterial array (count-prefixed)
    pointToVertex[]        compressed vertex index array
    vertexToPoint[]        compressed vertex index array
    nFaces                 uint32
    offsetSections         uint32
    _zero                  uint16
    faces[]                Polygon[nFaces] (each: byte polyType + vertex indices)
    sections[]             Section array (count-prefixed)
    namedSelections[]      NamedSelection array
    namedProperties[]      (key, value) string pairs
    keyframes[]            Keyframe array
    colorTop, color, special  int32, int32, int32
    vertexBoneRefIsSimple  bool
    sizeOfRestData         uint32
    clip[]                 condensed int array
    uvSets[]               UVSet (first read always, then n_uv_sets more)
    vertices[]             compressed Vector3P array (relative to boundingCenter!)
    normals[]              condensed compressed normal array
    stCoords[]             compressed float array
    vertexBoneRef[]        compressed array
    neighborBoneRef[]      compressed array
}
```

---

## 6. Fire Packer Container Format

Fire Packer is a DayZ PBO obfuscator by #Flipper#3241. When it processes a PBO:

1. Obfuscates file names (Cyrillic characters)
2. Adds fake PBO header entries
3. **Prepends data to .p3d files without updating LOD addresses**

### Detection
```python
data = open('file.p3d', 'rb').read()
if data[:4] != b'ODOL':
    odol_offset = data.find(b'ODOL')
    if odol_offset > 0:
        # Fire Packer container detected
        # ALL LOD addresses need odol_offset added
```

### LOD Address Correction
The ODOL header's LOD start/end addresses are relative to the original file.
Fire Packer prepends `odol_offset` bytes. Add `odol_offset` to each address.

---

## 7. Conversion Logic

Based on BisDLL `Conversion.cs` by T_D/Crip12.

### 7.1 Points
ODOL vertices are **relative to boundingCenter**. Add boundingCenter offset for MLOD absolute coordinates:
```python
for vi in range(n_verts):
    v = src.vertices[vi]
    pt.coords = (v.x + bc.x, v.y + bc.y, v.z + bc.z)
```

### 7.2 Faces
- Iterate ODOL sections (each section maps faces to a material)
- **Reverse winding order**: `vertex_indices[n-1-k]` instead of `[k]`
- UV from first UV set: `uv_data[vi * 2]`, `uv_data[vi * 2 + 1]`
- Texture from `section.texture_index → textures[]`
- Material from `section.material_index → materials[].material_name`

### 7.3 Named Selections
- ODOL `NamedSelection.selected_vertices` → py3d `Selection.points`
- ODOL `NamedSelection.selected_faces` → py3d `Selection.faces`
- Vertex weights from raw byte array (1 byte per selected vertex)

### 7.4 Mass
Distributed uniformly across all Geometry LOD points:
```python
if is_geometry_lod:
    mass_per_vert = total_mass / n_verts
```

### 7.5 Properties
Direct key-value string mapping to py3d `LOD.properties`.
