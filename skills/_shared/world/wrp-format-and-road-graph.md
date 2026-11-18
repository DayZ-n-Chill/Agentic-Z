# The `.wrp` world file: layout notes and road graph extraction

Notes on the binary layout of a DayZ `.wrp` (OPRW) world file and on how its road network becomes a road graph for a GPS style mod. The header facts were checked on the vanilla files on `P:\`. Everything else was measured on third party maps and is not checked on `P:\`. This repo ships no tool that reads `.wrp` files or builds a road graph; the steps below describe what such a tool has to do.

The terrain hole evidence (`terrain-holes-evidence.md`) leans on the same file format.

## OPRW layout

- **Header:** the bytes `OPRW`, an int32 version, then the sub magic `0FNE` ("ENF0" reversed). Both vanilla files on `P:\` read version 32: `P:\DZ\worlds\enoch\world\enoch.wrp` and `P:\DZ\worlds\chernarusplus\world\chernarusplus.wrp`. Versions 28 and 29, used by older maps, share one layout, apart from the 4 extra bytes per road link in v29 (see the Roadnet section).
- **`Models[]`:** a table of every `.p3d` path of the map, as zero terminated strings. It starts at the first `.p3d` string in the file; its count is the int32 four bytes before.
- **Roadnet section:** a grid of cells. Each cell is an int32 link count followed by that many road links. One road link is: connection count, positions, connection types, object id, 4 extra bytes in v29, the zero terminated `.p3d` path, and a 48 byte transform matrix. Find this section by scanning for the pattern, not by offset. It gives the base graph.
- **Object section:** after the Roadnet section and its zero padding. Its records have a fixed size of 60 bytes: `uint32 obj_id | uint32 model_idx | float matrix[12] | uint32 flags`. `model_idx` indexes `Models[]`, and the translation is `matrix[9..11]`. It holds every placed object: vegetation, buildings, rocks, and road pieces placed as loose objects that the Roadnet misses.
- **OPRW v32 object records:** in a mod map binarized by DayZ Tools 1.30.164078 the object records are 64 bytes, the 60 above plus a `uint32` at offset 60. That value was 0 in all 58,708 records of the one map read, and what it holds is not known. Reading every object at this size, the largest coordinate difference between 44,957 forest objects and their float64 placement records was below 0.49 mm, which is float32 rounding at x above 8,192 m. The object records of the two vanilla maps and the v32 Roadnet section were not measured.

## Building a road graph

1. Pull the `.wrp` out of the map's `world.pbo`.
2. Find the real world name (below). The output file has to carry it.
3. Build the base graph: read the Roadnet, remove duplicate nodes, then merge nodes that lie close together.
4. Run the connectivity passes (below).
5. Check the result by eye: one image of the graph, one image colored by connected component.
6. Ship the graph as `<worldname>_roads.json` and add the world name to the list of maps the consuming mod knows.

## The connectivity passes

1. **Road connector.** For each road piece in the Object section, connect the two nearest road nodes that are in different components and within 30 m (60 m for a bridge). The new edge is a three point line (node A, the piece's position, node B) with an asphalt surface. There is a real road model at that spot, which is what justifies the link. Track components with a union find that is updated as edges are added, so running the pass twice adds nothing.
2. **Reclassify.** Edges with surface `other` whose model belongs to a road family the base classifier does not know (`city_*`, `town_*` and similar) become asphalt.
3. **Stitch.** Node pairs in different components closer than 5 m get an edge marked as a stitch. This sews up fine fragmentation that the duplicate removal left.

Record in the output what each pass added, and keep a copy of each pass's input so a bad pass can be undone.

The rule behind them: never connect by distance alone. A real object from the `.wrp` has to justify each connection. Bridging node pairs only because they are within some maximum distance creates false connections.

On a modern custom map the largest connected component of the base graph already holds 90 to 97 % of the nodes, because its Roadnet is well built. The passes add little there, and what stays loose is usually a real island.

## World name is not the Workshop name

A mod that loads `<GetWorldName()>_roads.json` needs the engine's world name, not the title of the Workshop item and not the file name of the `.wrp`. `GetWorldName()` is at `P:\scripts\3_game\global\game.c:934`. The name is the world's class: vanilla Livonia is `class Enoch: CAWorld` in `CfgWorlds` (`P:\DZ\worlds\enoch\world\config.cpp:115`). For a Workshop map, read the class from the `config.bin` of its `world.pbo` (it is listed in `CfgWorldList` there).

- Two Workshop items can share one world name. Two Workshop versions of one map can both resolve to the same world name, as in one measured case; they cannot be installed together.
- Before writing code to tell two such items apart by version, compare the checksums of their `world.pbo` files. In the measured case both were byte identical, and one graph file served both.
- When the public PBOs carry no readable config (one measured map ships every `config.cpp` at 0 bytes), fall back in this order: the prefix in the header of `world.pbo`, usually `<WorldClass>\world`; the internal name of the `.wrp`, which by convention is the class in lower case; and the internal paths in the `.wrp`, which start with `<worldname>\data\`. Then confirm in game by printing `GetWorldName()` on the first test, and rename the graph file if the guess was wrong.

## The LZSS variant in PBO entries and rapified configs

A compressed PBO entry (packing method `Cprs`) and a compressed `config.bin` use LZSS, but not the classic ring buffer form. Back references are relative to the current end of the output:

```python
def bis_lzss(data, expected):
    out = bytearray(); src = 0; flags = 0
    while len(out) < expected and src < len(data):
        flags >>= 1
        if (flags & 0x100) == 0:
            flags = data[src] | 0xFF00; src += 1
        if flags & 1:                          # bit 1: a literal byte
            out.append(data[src]); src += 1
        else:                                  # bit 0: a relative back reference
            b1, b2 = data[src], data[src+1]; src += 2
            offset = b1 | ((b2 & 0xF0) << 4)    # 12 bits
            count  = (b2 & 0x0F) + 3           # 3 to 18
            if offset == 0: break
            start = len(out) - offset          # relative to the current length
            for k in range(count):
                i = start + k
                # a position before the start of the output reads as a space (0x20)
                out.append(out[i] if i >= 0 else 0x20)  # overlapping copies are allowed
    return bytes(out)
```

Two wrong assumptions cost time: a 4096 byte ring buffer that wraps around, and an absolute index in place of `len(out) - offset`. The 0x20 fill is real but only for positions before the start of the output; do not let Python's negative indexing read them from the end of the buffer.
