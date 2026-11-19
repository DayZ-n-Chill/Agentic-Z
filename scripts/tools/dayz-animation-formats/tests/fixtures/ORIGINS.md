# Animation test fixtures

Both binary files are test fixtures generated from literal semantic values.
They contain no game asset content.

## `seanim-v1-full.seanim`

- Written and read back by the Blender add-on `io_anim_seanim` at commit
  `dffe313b635ce8940264201f25db9e68f4486d7e`.
- Size: 288 bytes.
- SHA-256:
  `75af1c6ab01ae715e6cea01e6897b804586687ccf7a234c21be6bef871288b29`.

## `rtm-0101-mdat.rtm`

- Written and read back by Arma 3 Object Builder 2.5.1 under Blender 5.1.1.
- SHA-256 of that installation's `io/data_rtm.py`:
  `265c7c861ce1508e07c9a4034e8336745c1a70c33a3ea94121763401954b659e`.
- Size: 258 bytes.
- SHA-256:
  `37aa63f705d874c79b94721027d376a7cab347fc94691ad419e1172c5597c3f8`.

The JSON companions are hand-reviewed semantic expectations, independent of
the reader implemented in this tool.
