# Comparing two builds

How to tell what really changed between two builds of a mod: which entries can be compared by bytes, how to compare models, and why a hash pinned to a PBO or a file in git breaks on its own. Gates on a single build are in `post-build-gates.md`.

This is measured behaviour of AddonBuilder and git, not vanilla data, so it is not checked on `P:\`.

## Models are not byte stable between builds

With the same source MLOD and the same `-include`, two AddonBuilder runs give different `.p3d` bytes. The payload (vertices, normals, UVs, named selections, textures, material set) hashes the same; only the order of `faces`, `sections` and the material array changes. Of 10 byte-different entries in one comparison, 8 were pure reordering and 2 were the real change.

A second case, staging outside `P:\` and `-temp` under `P:\`: two builds in a row of one tree, with door and room MLODs byte identical, gave door ODOL entries of 339,554 and 339,551 bytes and room entries of 2,597,078 and 2,598,395 bytes, while every script, config, `.rvmat`, `.paa` and `.csv` entry hashed the same.

So:

- **Within one build**, byte identity holds and should be enforced: the binarized temp output must match the PBO entry exactly, since both come from the same run.
- **Between builds**, comparing `.p3d` bytes or sizes gives false alarms. An "only X should have changed" gate against the deployed PBO flags about 8 of 11 untouched entries.
- **Per-entry hashes are an identity gate for scripts, configs, materials and textures only.** A changed `.p3d` entry between two builds proves nothing by itself.
- **Accept a binarized model by the hash of its MLOD input plus an engine check** (render and raycast), never by ODOL bytes. Keep the MLOD hashes next to the PBO hash.
- **Do not chase a byte diff in a `.p3d` entry when the MLOD did not change.** If the doubt is already open, close it by content: extract the ODOL from each PBO and compare baked animations, bones, face counts and dimensions against the stage. In one case where `pbo_diff.py` showed 127 entries equal and the 10 `.p3d` different, those all matched.

## Comparing models by content

The gate between builds is an unordered multiset per LOD, keyed on `(material, texture, vertex index, lit bit)` and built by walking `sections` and mapping each face to its material. Vertex indices are comparable because vertex order is stable; its hash matches across runs. Work in three steps: counts, then payload, then the multiset.

If the sections do not cover every face of the LOD, the multiset is incomplete, and the gate must report itself void rather than pass.

## Scripts are byte stable

The reordering is in the ODOL of `.p3d` only. `.c` entries are byte stable between builds: in one comparison 1 of 147 `.c` entries changed size, and it was exactly the edited file, while all 50 `.p3d` sources were byte identical between the two trees. Comparing script entries between two PBOs is therefore a valid change detector; the "do not compare bytes between builds" rule is for `.p3d` only, and applying it to scripts throws away the cheapest gate there is.

## Compare the entries of two builds

After a rebuild, check that only the entries you meant to change differ:

```bat
python scripts/tools/dayz-pbo-diff/pbo_diff.py --old <old.pbo> --new <new.pbo> --out <diff.json>
```

It compares the SHA-256 of every entry's payload and the header properties; `differing` lists every entry that changed or is on one side only. Read it with the rule above: a different `.p3d` proves nothing by itself, a different script, config, material or texture does. `--ignore-prefix <prefix>` drops a prefix from `differing_not_ignored`, never from `differing`. A compressed entry is refused with exit 1; see `scripts/tools/dayz-pbo-diff/README.md`.

## A PBO pinned by hash cannot be rebuilt

If a release or an audit is pinned to a PBO's hash, rebuilding it "to regenerate it" gives a different hash from the same tree and breaks the pin without a word. In such a project, never rebuild the PBO: it is a unique file, so back it up by hash.

Every expected difference needs a pinned base. Audit gate code for `continue`, `pass`, `ok += 1` and allow lists. A file known to differ because a merge is not yet promoted cannot get an unconditional pass: store the SHA-256 of the exact source base when it is derived (in a file such as `enforce-base.json`), mark the result stale if that base moved, and force the merge to be rebuilt. A separate check for words such as "retired" or "obsolete" answers a different question; require the live identifier beside each retired reference.

## Hashes pinned in git change on checkout

With `core.autocrlf=true`, the Windows default, `git add` stores LF and `git checkout` writes CRLF, so the blob and the working tree stop matching pinned sizes and hashes. One text file of 1577 bytes was pinned against the blob's 1548, and a Windows clone showed 8 failures. Run the gate on a freshly checked out clone, not on a copy made with robocopy: the copy keeps the original bytes and passes on a tree nobody receives. Commit a `.gitattributes` with `* text=auto eol=lf` from the first commit, plus `-text` on whatever is compared byte by byte.

## Trace a release to its whole source tree

Trace a release PBO to its commit by the hash of its entire source tree, not of the files you touched. Before a release, check the chain from the commit or canonical source through the full build tree to the PBO. An incremental sync that reports "verified" only checks its own changes.

## Script memory is not PBO size

A smaller PBO is no evidence of a smaller script footprint. When the goal is script memory, never judge it from source bytes, line counts or PBO size; the size is an identity check, not a proxy for compiled memory. Measure the control and the candidate in DayZDiag with the same mod stack and order, mission and config, and report Game, World, Mission and total separately, along with the file and class counts and the hashes. Only a delta that repeats in the engine supports a claim about cause or capacity.
