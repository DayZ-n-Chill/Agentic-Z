# Third-party notices

Agentic-Z's own license is in [`LICENSE`](LICENSE). Some of the code and text in this repo comes from other people's projects. That material stays under its own license, and this file carries the copyright notices and license texts those licenses ask for. Most of it was reworked when it came in, so many files here differ from the upstream ones.

## DayZ Modding Knowledge Pack

- Upstream: [willy92wins/DayZ-Modding-Knowledge-Pack](https://github.com/willy92wins/DayZ-Modding-Knowledge-Pack)
- License: MIT (text below)
- Copyright: Copyright (c) 2026 DayZ Modding Knowledge Pack contributors

The Knowledge Pack's skills, notes and tools were imported and then merged into this repo's own folders. Its material now lives in:

- **The knowledge packs** under `skills/_shared/`: `ai/`, `animation/`, `audio-fx/`, `enscript/`, `models/`, `persistence/`, `physics/`, `textures/`, `ui/`, `vehicles/`, `weapons/`, `wearables/` and `world/`, plus `skills/_shared/linux-proton.md` and `skills/_shared/viewer_core.py`.
- **Two skills built from it**: `skills/dayz-animation-pipeline/` and `skills/dayz-model-tools/`.
- **References and scripts added to existing skills**: `skills/dayz-build-pbo/references/` and `skills/dayz-build-pbo/pbo_entries.py`, `skills/dayz-import-mod/references/` and `skills/dayz-import-mod/pbo_inventory.py`, `skills/dayz-launch-test/references/` and `skills/dayz-launch-test/assets/autotest-mod/`, `skills/dayz-layout-preview/gen_panel_layout.py`, `skills/dayz-p3d-audit/references/` and `skills/dayz-p3d-audit/scripts/`, `skills/dayz-pack-texture/scripts/`, `skills/dayz-particles/references/`, `skills/dayz-preflight/references/` and `skills/dayz-scope-mod/references/`.
- **The offline tools** under `scripts/tools/`: `dayz-3d-viewer/`, `dayz-animation-formats/`, `dayz-layout-viewer/`, `dayz-linux/`, `dayz-model-preflight/`, `dayz-navmesh-compare/`, `dayz-odol-strict/`, `dayz-pbo-diff/`, `dayz-persistence-contracts/`, `dayz-script-validator/`, `dayz-terrain-builder-runner/`, `dayz-ui-lab/`, `dayz-vehicle-proxy-contract/`, `py3d/`, `viewer-gate/` and `sync_generated.py`.
- **Smaller pieces**: `scripts/dev/pack_skill.py` and the fixtures in `evals/fixtures/dayz-script-specialist/`.

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

## py3d

- Upstream: [KoffeinFlummi/py3d](https://github.com/KoffeinFlummi/py3d). The copy here is the Knowledge Pack's DayZ fork of it.
- License: MIT (text below, and in [`scripts/tools/py3d/LICENSE`](scripts/tools/py3d/LICENSE))
- Copyright: Copyright (c) 2017 Felix Wiegand
- Where it lives: `scripts/tools/py3d/`

```text
The MIT License (MIT)

Copyright (c) 2017 Felix Wiegand

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

## bzed/dayz-dev-plugin (contributed parts only)

- Upstream: `bzed/dayz-dev-plugin` at commit `6112ac5`
- License: MIT. The plugin repository itself is GPL; its author contributed the parts listed here to the Knowledge Pack under the Knowledge Pack's MIT license, so the MIT text printed above for the Knowledge Pack covers them.
- Copyright: held by the author of those parts (bzed)
- Where it lives:
  - nine helper scripts in `scripts/tools/dayz-linux/`: `find-dayzserver.sh`, `make-server-tree.sh`, `free-ports.sh`, `dayz-client-headless.sh`, `dayz-client-test.sh`, `dayz-mod-pack.sh`, `extract-dayz-sources.sh`, `build-api-index.py` and `dayz-api.py`, with their test `scripts/tools/dayz-linux/test_linux_helpers.py`
  - the test mod in `skills/dayz-launch-test/assets/autotest-mod/`
  - the references `skills/dayz-launch-test/references/linux-native-server.md`, `skills/dayz-launch-test/references/linux-headless-client.md`, `skills/dayz-launch-test/references/dayz-1-30-server-measured.md` and `skills/dayz-build-pbo/references/dayzmake-linux.md`

## img2threejs

- Upstream: [img2threejs/img2threejs](https://github.com/img2threejs/img2threejs) at commit `9a8ecf129a58c1b557a1f03f7727f6295672cd51` (v1.4.3)
- License: Apache License 2.0 (text at the end of this file)
- Copyright: the img2threejs authors. No upstream copyright line or `NOTICE` file was recorded when it was imported.
- Where it lives, and what was changed:
  - `skills/dayz-model-tools/scripts/correction_loop.py`: a copy of upstream `forge/stage4_review/correction_loop.py`, unchanged.
  - `skills/dayz-model-tools/scripts/vr_delta.py`: **changed.** Adapted to compare two Blender renders taken from the same camera, from upstream `forge/stage1_intake/extract_pbr_evidence.py` (PNG decoding and the foreground mask), `forge/stage4_review/diagnose_render.py` (mask geometry) and `forge/stage4_review/divine_eye.py` (brightness signals).
  - Method text adapted from the upstream `SKILL.md` and `grimoire/` rubrics: the bounded correction loop in `skills/_shared/models/blender-visual-review.md`, and the zone by zone detail scan in `skills/_shared/models/blender-detail-scan.md`. Both were rewritten.

## Dev-GOM blender-toolkit

- Upstream: [Dev-GOM/claude-code-marketplace](https://github.com/Dev-GOM/claude-code-marketplace), `plugins/blender-toolkit`
- License: Apache License 2.0 (text at the end of this file)
- Copyright: Dev-GOM. The upstream files carry no license header, and no upstream `NOTICE` file was recorded when they were imported.
- Where it lives, and what was changed:
  - `skills/dayz-animation-pipeline/scripts/retargeting.py`: **changed.** Imports flattened, the logger replaced with standard library logging, and comments and docstrings translated from Korean to English.
  - `skills/dayz-animation-pipeline/scripts/bone_matching.py`: **changed**, in the same ways.
  - `skills/_shared/animation/mixamo-bone-mapping.md`: **changed.** Rewritten from upstream's bone mapping guide and corrected.

## Apache License 2.0

The license of the img2threejs and Dev-GOM blender-toolkit material listed above.

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
