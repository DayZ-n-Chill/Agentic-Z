# Third-party notices

Agentic-Z's own license is in [`LICENSE`](LICENSE). Parts of this repo were brought in from other projects. Those parts stay under the licenses listed here, and this file carries the notices those licenses ask for.

## DayZ Modding Knowledge Pack

- Upstream: [willy92wins/DayZ-Modding-Knowledge-Pack](https://github.com/willy92wins/DayZ-Modding-Knowledge-Pack)
- License: MIT
- Copyright: Copyright (c) 2026 DayZ Modding Knowledge Pack contributors

Where its material lives in this repo:

- **The knowledge packs under `skills/_shared/`.** The pack `skills/_shared/knowledge/` is new. The Knowledge Pack's material was merged into the packs `ai/`, `animation/`, `audio-fx/`, `enscript/`, `enscript-style/`, `models/`, `persistence/`, `physics/`, `textures/`, `vehicles/`, `weapons/` and `wearables/`. `skills/_shared/scripts/`, `skills/_shared/viewer_core.py`, `skills/_shared/linux-proton.md` and `skills/_shared/skill-resolution.md` came with it too.
- **The imported skills**, one folder each under `skills/`: `3d-generation-harness`, `ai-3d-to-dayz`, `ardy-motion-generation`, `blender-animation`, `blender-assembly`, `blender-visual-review`, `dayz-3d-viewer`, `dayz-ai-patterns`, `dayz-animation-pipeline`, `dayz-aviation`, `dayz-basebuilding`, `dayz-characters`, `dayz-clothing`, `dayz-doors`, `dayz-environment-hazards`, `dayz-feature-spec`, `dayz-mcp-verify`, `dayz-mod-dev`, `dayz-mod-workflow`, `dayz-model-pipeline`, `dayz-motorbikes`, `dayz-p3d-inspector`, `dayz-pbo-reverse-engineering`, `dayz-persistence`, `dayz-physics-engine`, `dayz-proxy-align`, `dayz-realistic-animation-director`, `dayz-sound-system`, `dayz-test-ingame`, `dayz-texture-pipeline`, `dayz-ui-development`, `dayz-underground`, `dayz-vehicles`, `dayz-weapons`, `enforce-script-reference`, `mixamo-retarget`, `rigorous-data-audit`, `rip-vehicle-import`, `systematic-debugging`, `task-observer`, `uv-clean-atlas`.
- **Existing skills that took in Knowledge Pack material**: `skills/dayz-build-pbo/`, `skills/dayz-lint/`, `skills/dayz-p3d-audit/`, `skills/dayz-particles/` and `skills/dayz-preflight/`.
- **`scripts/tools/`**: the Knowledge Pack's tools.
- **`scripts/dev/knowledge-pack/`**: the Knowledge Pack's own validation, packaging and promotion tooling.
- **Evals and docs**: `evals/cases/`, `evals/schema.json`, `evals/live/`, the questions converted from its cases in `evals/questions/`, and `docs/compatibility-matrix.md`, `docs/dayz-mcp.md` and the four `docs/knowledge-pack-*.md` files.

The material was translated, reorganized and corrected during the import, so most of these files differ from the upstream ones.

```text
MIT License

Copyright (c) 2026 DayZ Modding Knowledge Pack contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Bundled third-party components

The Knowledge Pack bundled work by other authors. Each component below is in this repo at the paths given.

### py3d

- Upstream: [KoffeinFlummi/py3d](https://github.com/KoffeinFlummi/py3d). The copy here is the Knowledge Pack's DayZ fork of it.
- License: MIT
- Copyright: Copyright (c) 2017 Felix Wiegand
- Paths: `scripts/tools/py3d/`
- License file: [`scripts/tools/py3d/LICENSE`](scripts/tools/py3d/LICENSE)

### bzed/dayz-dev-plugin (contributed parts only)

- Upstream: `bzed/dayz-dev-plugin` at commit `6112ac5`
- License: MIT. The plugin repository itself is GPL; its author contributed the parts listed here to the Knowledge Pack under MIT, as the Knowledge Pack's notices state.
- Copyright: held by the author of those parts (bzed)
- Paths:
  - nine helper scripts in `skills/_shared/scripts/`: `find-dayzserver.sh`, `make-server-tree.sh`, `free-ports.sh`, `dayz-client-headless.sh`, `dayz-client-test.sh`, `dayz-mod-pack.sh`, `extract-dayz-sources.sh`, `build-api-index.py` and `dayz-api.py`. Each keeps its `# Source:` line.
  - `skills/_shared/scripts/test_linux_helpers.py`
  - `skills/dayz-test-ingame/assets/autotest-mod/`
  - `skills/dayz-mod-dev/SKILL.md`
  - the references `skills/dayz-test-ingame/references/linux-native-server.md`, `skills/dayz-test-ingame/references/linux-headless-client.md`, `skills/dayz-build-pbo/references/dayzmake-linux.md` and `skills/dayz-mod-workflow/references/dayz-1-30-server-measured.md`

These parts are covered by the MIT permission notice printed above for the Knowledge Pack, with the copyright held by their author.

### obra/superpowers: systematic-debugging

- Upstream: [obra/superpowers](https://github.com/obra/superpowers), `skills/systematic-debugging`
- License: MIT
- Copyright: Copyright (c) 2025 Jesse Vincent
- Paths: `skills/systematic-debugging/SKILL.md` and `skills/systematic-debugging/references/` (`root-cause-tracing.md`, `defense-in-depth.md`, `condition-based-waiting.md`, `condition-based-waiting-example.ts`)
- Changes: the Knowledge Pack left out the upstream `CREATION-LOG.md`, `SCORE.json`, `find-polluter.sh` and `test-*.md`. During the import into this repo the companion files moved into `references/`, and `SKILL.md` and the three Markdown references were edited. `condition-based-waiting-example.ts` is unchanged.

```text
MIT License

Copyright (c) 2025 Jesse Vincent

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

### rebelytics: task-observer ("One Skill to Rule Them All")

- Upstream: [rebelytics/one-skill-to-rule-them-all](https://github.com/rebelytics/one-skill-to-rule-them-all)
- Author: Eoghan Henn / [rebelytics.com](https://rebelytics.com)
- License: Creative Commons Attribution 4.0 International (CC BY 4.0), <https://creativecommons.org/licenses/by/4.0/>. The full legal code is at <https://creativecommons.org/licenses/by/4.0/legalcode>.
- Paths: `skills/task-observer/SKILL.md` and `skills/task-observer/references/` (`environments.md`, `migration.md`, `observation-log.md`, `signals.md`, `skill-authoring.md`, `weekly-review.md`)
- Changes were made. The Knowledge Pack softened the session-start trigger, so the skill observes only while work is in progress, and left out the upstream `README.md`, `USER-GUIDE.md`, `CONTRIBUTING.md`, `SCORE.json`, images, CI and plugin files and `scripts/`. During the import into this repo `SKILL.md` and all six references were edited further, and the credit block that stood at the top of `SKILL.md` was replaced by this notice.

### img2threejs

- Upstream: [img2threejs/img2threejs](https://github.com/img2threejs/img2threejs) at commit `9a8ecf129a58c1b557a1f03f7727f6295672cd51` (v1.4.3)
- License: Apache License 2.0 (text below)
- Copyright: the img2threejs authors. The Knowledge Pack records no copyright line and no upstream `NOTICE` file for it.
- Paths and changes:
  - `skills/blender-visual-review/correction_loop.py`: the Knowledge Pack describes it as a verbatim copy of upstream `forge/stage4_review/correction_loop.py`. It is unchanged from the Knowledge Pack's copy.
  - `skills/blender-visual-review/vr_delta.py`: **changed file.** The Knowledge Pack adapted it for pairs of Blender renders taken from the same camera: the PNG codec and foreground mask from `forge/stage1_intake/extract_pbr_evidence.py`, the mask geometry from `forge/stage4_review/diagnose_render.py` and the luma signals from `forge/stage4_review/divine_eye.py`. Its docstring lists these origins. In this repo the one docstring line that names the license now points at this file.
  - Method text adapted from the upstream `SKILL.md` and `grimoire/` rubrics: the bounded loop, typed actions and per-feature gates in `skills/blender-visual-review/SKILL.md`, and the detail scan protocol in `skills/blender-assembly/references/detail-scan.md`.

### Dev-GOM blender-toolkit

- Upstream: [Dev-GOM/claude-code-marketplace](https://github.com/Dev-GOM/claude-code-marketplace), `plugins/blender-toolkit`
- License: Apache License 2.0 (text below)
- Copyright: Dev-GOM. The Knowledge Pack records no copyright line and no upstream `NOTICE` file for it, and the files carry no license header.
- Paths and changes:
  - `skills/mixamo-retarget/scripts/retargeting.py`: **changed file.** The Knowledge Pack flattened the relative imports and replaced the logger with standard-library logging. In this repo the comments and docstrings were translated from Korean to English.
  - `skills/mixamo-retarget/scripts/bone_matching.py`: **changed file.** The same changes as `retargeting.py`.
  - `skills/mixamo-retarget/references/bone-mapping-guide.md`: **changed file.** Corrected in this repo, with the commands that exist only in the upstream toolkit marked as such.
- Not included: the upstream WebSocket command-line control plane and its confirmation panel.

### Apache License 2.0

The license of the img2threejs and Dev-GOM blender-toolkit files listed above.

```text
                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

   1. Definitions.

      "License" shall mean the terms and conditions for use, reproduction,
      and distribution as defined by Sections 1 through 9 of this document.

      "Licensor" shall mean the copyright owner or entity authorized by
      the copyright owner that is granting the License.

      "Legal Entity" shall mean the union of the acting entity and all
      other entities that control, are controlled by, or are under common
      control with that entity. For the purposes of this definition,
      "control" means (i) the power, direct or indirect, to cause the
      direction or management of such entity, whether by contract or
      otherwise, or (ii) ownership of fifty percent (50%) or more of the
      outstanding shares, or (iii) beneficial ownership of such entity.

      "You" (or "Your") shall mean an individual or Legal Entity
      exercising permissions granted by this License.

      "Source" form shall mean the preferred form for making modifications,
      including but not limited to software source code, documentation
      source, and configuration files.

      "Object" form shall mean any form resulting from mechanical
      transformation or translation of a Source form, including but
      not limited to compiled object code, generated documentation,
      and conversions to other media types.

      "Work" shall mean the work of authorship, whether in Source or
      Object form, made available under the License, as indicated by a
      copyright notice that is included in or attached to the work
      (an example is provided in the Appendix below).

      "Derivative Works" shall mean any work, whether in Source or Object
      form, that is based on (or derived from) the Work and for which the
      editorial revisions, annotations, elaborations, or other modifications
      represent, as a whole, an original work of authorship. For the purposes
      of this License, Derivative Works shall not include works that remain
      separable from, or merely link (or bind by name) to the interfaces of,
      the Work and Derivative Works thereof.

      "Contribution" shall mean any work of authorship, including
      the original version of the Work and any modifications or additions
      to that Work or Derivative Works thereof, that is intentionally
      submitted to Licensor for inclusion in the Work by the copyright owner
      or by an individual or Legal Entity authorized to submit on behalf of
      the copyright owner. For the purposes of this definition, "submitted"
      means any form of electronic, verbal, or written communication sent
      to the Licensor or its representatives, including but not limited to
      communication on electronic mailing lists, source code control systems,
      and issue tracking systems that are managed by, or on behalf of, the
      Licensor for the purpose of discussing and improving the Work, but
      excluding communication that is conspicuously marked or otherwise
      designated in writing by the copyright owner as "Not a Contribution."

      "Contributor" shall mean Licensor and any individual or Legal Entity
      on behalf of whom a Contribution has been received by Licensor and
      subsequently incorporated within the Work.

   2. Grant of Copyright License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      copyright license to reproduce, prepare Derivative Works of,
      publicly display, publicly perform, sublicense, and distribute the
      Work and such Derivative Works in Source or Object form.

   3. Grant of Patent License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      (except as stated in this section) patent license to make, have made,
      use, offer to sell, sell, import, and otherwise transfer the Work,
      where such license applies only to those patent claims licensable
      by such Contributor that are necessarily infringed by their
      Contribution(s) alone or by combination of their Contribution(s)
      with the Work to which such Contribution(s) was submitted. If You
      institute patent litigation against any entity (including a
      cross-claim or counterclaim in a lawsuit) alleging that the Work
      or a Contribution incorporated within the Work constitutes direct
      or contributory patent infringement, then any patent licenses
      granted to You under this License for that Work shall terminate
      as of the date such litigation is filed.

   4. Redistribution. You may reproduce and distribute copies of the
      Work or Derivative Works thereof in any medium, with or without
      modifications, and in Source or Object form, provided that You
      meet the following conditions:

      (a) You must give any other recipients of the Work or
          Derivative Works a copy of this License; and

      (b) You must cause any modified files to carry prominent notices
          stating that You changed the files; and

      (c) You must retain, in the Source form of any Derivative Works
          that You distribute, all copyright, patent, trademark, and
          attribution notices from the Source form of the Work,
          excluding those notices that do not pertain to any part of
          the Derivative Works; and

      (d) If the Work includes a "NOTICE" text file as part of its
          distribution, then any Derivative Works that You distribute must
          include a readable copy of the attribution notices contained
          within such NOTICE file, excluding those notices that do not
          pertain to any part of the Derivative Works, in at least one
          of the following places: within a NOTICE text file distributed
          as part of the Derivative Works; within the Source form or
          documentation, if provided along with the Derivative Works; or,
          within a display generated by the Derivative Works, if and
          wherever such third-party notices normally appear. The contents
          of the NOTICE file are for informational purposes only and
          do not modify the License. You may add Your own attribution
          notices within Derivative Works that You distribute, alongside
          or as an addendum to the NOTICE text from the Work, provided
          that such additional attribution notices cannot be construed
          as modifying the License.

      You may add Your own copyright statement to Your modifications and
      may provide additional or different license terms and conditions
      for use, reproduction, or distribution of Your modifications, or
      for any such Derivative Works as a whole, provided Your use,
      reproduction, and distribution of the Work otherwise complies with
      the conditions stated in this License.

   5. Submission of Contributions. Unless You explicitly state otherwise,
      any Contribution intentionally submitted for inclusion in the Work
      by You to the Licensor shall be under the terms and conditions of
      this License, without any additional terms or conditions.
      Notwithstanding the above, nothing herein shall supersede or modify
      the terms of any separate license agreement you may have executed
      with Licensor regarding such Contributions.

   6. Trademarks. This License does not grant permission to use the trade
      names, trademarks, service marks, or product names of the Licensor,
      except as required for reasonable and customary use in describing the
      origin of the Work and reproducing the content of the NOTICE file.

   7. Disclaimer of Warranty. Unless required by applicable law or
      agreed to in writing, Licensor provides the Work (and each
      Contributor provides its Contributions) on an "AS IS" BASIS,
      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
      implied, including, without limitation, any warranties or conditions
      of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A
      PARTICULAR PURPOSE. You are solely responsible for determining the
      appropriateness of using or redistributing the Work and assume any
      risks associated with Your exercise of permissions under this License.

   8. Limitation of Liability. In no event and under no legal theory,
      whether in tort (including negligence), contract, or otherwise,
      unless required by applicable law (such as deliberate and grossly
      negligent acts) or agreed to in writing, shall any Contributor be
      liable to You for damages, including any direct, indirect, special,
      incidental, or consequential damages of any character arising as a
      result of this License or out of the use or inability to use the
      Work (including but not limited to damages for loss of goodwill,
      work stoppage, computer failure or malfunction, or any and all
      other commercial damages or losses), even if such Contributor
      has been advised of the possibility of such damages.

   9. Accepting Warranty or Additional Liability. While redistributing
      the Work or Derivative Works thereof, You may choose to offer,
      and charge a fee for, acceptance of support, warranty, indemnity,
      or other liability obligations and/or rights consistent with this
      License. However, in accepting such obligations, You may act only
      on Your own behalf and on Your sole responsibility, not on behalf
      of any other Contributor, and only if You agree to indemnify,
      defend, and hold each Contributor harmless for any liability
      incurred by, or claims asserted against, such Contributor by reason
      of your accepting any such warranty or additional liability.

   END OF TERMS AND CONDITIONS
```

## Adapted ideas, with no third-party code bundled

- **GitHub Spec Kit** ([github/spec-kit](https://github.com/github/spec-kit), MIT): `skills/dayz-feature-spec/` adapts the idea of specification-driven development. No Spec Kit file is bundled.
- **SE2Dev io_anim_seanim** ([SE2Dev/io_anim_seanim](https://github.com/SE2Dev/io_anim_seanim) at commit `dffe313b635ce8940264201f25db9e68f4486d7e`, MIT): `scripts/tools/dayz-animation-formats/` writes and reads the SEAnim version 1 format and used that project as an independent reader and writer to check against. The fixture `scripts/tools/dayz-animation-formats/tests/fixtures/seanim-v1-full.seanim` was generated with it. No SE2Dev source is bundled.
- **Arma 3 Object Builder** ([MrClock8163/Arma3ObjectBuilder](https://github.com/MrClock8163/Arma3ObjectBuilder), GPL-3.0-or-later): the fixture `scripts/tools/dayz-animation-formats/tests/fixtures/rtm-0101-mdat.rtm` was generated with version 2.5.1. No source of it is bundled. `scripts/tools/dayz-animation-formats/tests/fixtures/ORIGINS.md` records how both fixtures were made.
- **Bohemia Interactive PAA LZSS variant**: `scripts/tools/dayz-3d-viewer/` reimplements the LZSS variant used on PAA mipmaps that are not DXT compressed, as the Bohemia Interactive Community Wiki documents it. No third-party source is bundled.

## Used at run time, not bundled

Nothing from these projects is in this repo: three.js (MIT; the generated viewer pages load it from a CDN, and the `skills/rip-vehicle-import/classify-viewer/` page expects the user to fetch it), Blender and its Python API, numpy, Pillow, dayzmake, DayZ-MCP, and the external ODOL reader that `scripts/tools/dayz-odol-strict/` pins by manifest. DayZ game scripts, tools and data belong to Bohemia Interactive and are quoted by path and line only.
