# /dayz-import-mod: GitHub links and cleanup

Detail for `/dayz-import-mod`. The skill's `SKILL.md` has the short version.

## Accepted git links

- `https://github.com/<owner>/<repo>`, with or without `.git` or `https://`
- `https://github.com/<owner>/<repo>/tree/<branch>` clones that branch. A branch name with a slash, such as `feature/x`, works.
- `https://github.com/<owner>/<repo>/tree/<branch>/<folder>` imports that subfolder as the mod (see below).
- Any other `https://.../<repo>.git` or `git@host:.../<repo>.git` remote.

`git` must be on `PATH`, and a private repo needs your usual git credentials.

## Repo link (no subfolder)

- The mod name comes from the repo name, or from `--name`.
- A name the rule refuses, such as `DayZ-Expansion` with its hyphen, needs `--name` (for example `--name DayZExpansion`). The paste-in hook suggests the command with a valid `--name` already filled in.
- The repo is cloned with `git` straight into `workspace/<ModName>/` as a real folder, because a clone has no other home on disk.
- It then gets the same `P:\<ModName>\` junction, project cache update and scaffold check as a folder import. Accepted pieces are written into the clone.
- The scaffold check looks at the repo root. For a repo that keeps the mod in a subfolder, paste the tree link to that subfolder instead.
- The same refusals apply before anything is cloned: the name, an existing `workspace/<Name>/`, and a `P:\<Name>\` that points elsewhere.
- If a later step refuses (missing pieces with no `--scaffold` or `--no-scaffold` and no interactive console, or the junction fails), the clone is deleted again so a retry starts clean.

## Tree link to a subfolder

- A link such as `tree/main/MyMod` treats the subfolder as the mod. The mod name comes from the subfolder name, or from `--name`.
- The whole repo is cloned to `.imports\<owner>__<repo>__<branch>\`. That folder is gitignored and outside `workspace/`.
- There is one clone per owner, repo and branch. A clone is reused only when another subfolder of that same branch is imported, so a second branch or a fork never picks up another clone's files.
- `workspace/<ModName>` is then linked to the subfolder exactly as a folder import is. The scaffold check and any accepted pieces go into the subfolder, never the repo root.
- A subfolder that contains `..`, or that resolves outside the clone, is refused.
- If the folder is not in the branch, the run refuses. A reused clone may just be out of date, so the error gives the `git pull` to run.
- When the run refuses (missing folder, missing pieces with no decision flag and no interactive console, or a failed link), a clone this run made is deleted again. A clone from an earlier import is never deleted.

## Cleanup

`/dayz-clean-workspace --mod <Name>` recognizes imported mods automatically:

- The `workspace/<Name>/` link is removed with `cmd /c rmdir`, with no recursion into the link target. Your source folder is never touched.
- The `P:\<Name>\` junction is removed, but only when its target matches `workspace/<Name>/`.
- The `P:\Mods\@<Name>\` deployed folder is removed if it has the Agentic-Z ownership marker (written by `/dayz-build-pbo` and `/dayz-deploy-pbo`).
- The plan labels an imported mod `(workspace-link) workspace\MyMod` (link removed, source kept) and a native scaffold `(workspace) workspace\NativeMod` (folder and contents removed).

Cloned imports need extra steps:

- A repo-link clone lives in `workspace/<Name>/` and holds `.git`. `/dayz-clean-workspace` never deletes a folder that holds `.git`, so it refuses and prints the `rmdir` commands. Push anything you want to keep, then delete the folder by hand (`cmd /c rmdir /s /q workspace\<Name>`) and remove the junction (`cmd /c rmdir P:\<Name>`). The import prints both commands at the end.
- For a subfolder import, `/dayz-clean-workspace --mod <Name>` removes the links. Delete the clone under `.imports\` by hand.
