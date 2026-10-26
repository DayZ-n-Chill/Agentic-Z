# How the indexer chunks each file type

The rules below are what `index.py` does; the constants named are in that file.

| File type | Chunking |
|---|---|
| `.c .cpp .hpp .h .cfg .layout` | One chunk per top-level `class X { ... }` block, whole file if there are none. The code between classes (global functions, enums, typedefs, constants, and the rest of the file after a class that never closes) gets its own chunks with an empty parent context; a gap of only comments is skipped. Braces and `class` words inside comments and strings are ignored, so a `}` in a comment does not end a class early. A block or file over 6,000 characters (`EMBED_MAX_CHARS`) is split into windows of at most that size, cut at member boundaries (a method or field starting at the class's top level) where possible, otherwise at the last whole line that fits. Each window keeps the class name as parent context and its own real line range, so no script text is dropped. |
| `.rvmat` | Whole file, deduplicated by SHA-256 of the content. |
| `.xml` | Whole file under 4 KB. A larger file with 5 or more top-level elements is cut into slices of its own lines: each element's slice runs from the line after the previous element to its own end line, so the comments above it (commented-out entries included) travel with it, and elements on one line stay together. Slices are batched until the next would pass 6,000 characters (at most 50 elements, `XML_BATCH_SIZE`); a slice over 6,000 characters on its own is split into windows. The XML declaration and the root's own start and end tags are left out, unless a comment sits before the root or after the last element, in which case those lines are kept too. A file with fewer elements, or one that does not parse, is windowed like JSON. |
| `.json .csv` | Whole file up to 6,000 characters, otherwise windows of at most that size with their real line ranges. Each CSV window starts with the file's header line, so a stringtable row still names its language columns. The header is repeated only when it is at most 3,000 characters (half the window); a wider header is in the first window only. Vanilla has one CSV, `P:\languagecore\stringtable.csv`, and its header (line 1) is 158 characters with its line break. |

Only `.rvmat` is cut: a chunk stores at most 4,000 characters of the material. Every other chunk is at most 6,000 characters and is stored and embedded whole, and the windows and slices of a file together hold all of its text (for XML, all of the text inside the root element).

Each chunk stores path, file type, parent context (class name, XML range, or rvmat hash), line range and content.

## Indexes built by older versions

- Indexes built before windowing stored only the first 8,000 characters of each oversize class block, XML batch, JSON file or CSV file, so most stringtable rows were never searchable.
- Indexes built before file-scope chunks have no chunks for the code between classes (enums, typedefs, globals). A downloaded release built before that change has none either.

Both are fixed by one `--full` rebuild, which is a paid embedding run; expect the chunk count to rise.
