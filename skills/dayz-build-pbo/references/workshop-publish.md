# Signing and publishing to the Workshop

How to sign a built PBO with DsUtils, lay out the Workshop item folder, and publish it to the Steam Workshop (DayZ is app 221100) with the Publisher or SteamCMD. The release texts (description, changelog, class name list) come from `/dayz-release-pack`; the Linux route is in `dayzmake-linux.md`.

This is tool and Steam behaviour, measured on one Windows PC with the Steam client signed in, not vanilla data. Signing, creating a hidden item with SteamCMD and what a SteamCMD login does to the Steam client were measured. Updating an item and the subscriber's side (the download, the `!Workshop` junction and `meta.cpp`) were not.

## Licence limits

Content built with DayZ Tools is non-commercial under the DayZ Tools EULA, reuse of Bohemia game data falls under Bohemia's non-commercial terms, and content may not sit behind a paywall; voluntary donations and free content are allowed. This matters most for mods built from ripped or AI-generated assets. Read Bohemia's current EULA and monetization rules before publishing.

## The item folder

```text
addons\<Mod>.pbo
addons\<Mod>.pbo.<authority>.bisign
keys\<authority>.bikey
mod.cpp
```

The `.biprivatekey` never goes into the item or the repository.

## Signing with DsUtils

The DsUtils tools are in `Bin\DsUtils` under DayZ Tools.

| Tool | What it does |
|---|---|
| `DSCreateKey <authority>` | Writes the key pair. |
| `DSSignFile <authority>.biprivatekey <Mod>.pbo` | Writes the `.bisign` beside the PBO. |
| `DSCheckSignatures <addons folder> <keys folder>` | Prints `Signature ... is OK` for a good signature. |

The `.bisign` is a separate file: the PBO hashed the same before and after signing. The three tools write `.RPT` and `.mdmp` files next to their own executable, so run a copy of them from a folder of your own.

## Publisher or SteamCMD

| | Publisher (DayZ Tools) | SteamCMD |
|---|---|---|
| Steam session | The running Steam client's (read from its files, not measured) | Its own login with an account |
| Command line | None in DayZ Tools | `+workshop_build_item <vdf>` |
| On a machine where people play | No second login (read from its files, not measured) | Kicks the Steam client off when it logs in with the client's account (below) |

`Bin\Publisher\Publisher.exe` is a 32-bit WPF application signed by Bohemia Interactive. It reaches Steam through `steam_api.dll`, with `steam_appid.txt` holding 221100, and its strings include `SteamAPI_Init`, `IsSteamRunning` and "Publisher requires that the Steam client is online". DayZ Tools ships no `PublisherCmd` (the command-line publisher of Arma 3 Tools), and the Publisher's strings show no command-line option. This was read from the installed files without running them. From those strings the Publisher publishes with the running client's session instead of logging in; that, and whether it disturbs the session, is not measured.

## A SteamCMD login replaces the client's session

A SteamCMD login with the account the Steam client has signed in on the same machine takes over the client's session. In the same second as SteamCMD's `LogOnResponse` OK, the client's `logs\connection_log.txt` recorded `RecvMsgClientLoggedOff('Session Replaced')` and `not auto reconnecting due to Session Replaced`. The client did not reconnect by itself and stayed offline until it was restarted. Meanwhile, game joins on that machine were kicked with code 49 in `WaitAuthPlayerLoginState`. `HKCU\Software\Valve\Steam\ActiveProcess` did not change, so a registry check misses it; the client's `connection_log.txt` shows it.

So on a machine where people play, publish with the Publisher, or run SteamCMD with that account only while the Steam client is closed and no game is running, the first login included. A second account was not tried. Not measured, but expected: any SteamCMD login with that account does the same, `workshop_download_item` included.

## Logging in to SteamCMD

1. Download `https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip` and check that `Get-AuthenticodeSignature steamcmd.exe` reports `Valid` with a Valve signer before running it.
2. Do the first run by hand. It updates itself (about 43 MB) and relaunches, and the relaunched process loses a `+quit` given on the command line.
3. The account owner logs in once: `login <account>` and the password. The first attempt answers `Account Logon Denied` and asks for the Steam Guard code. Then `quit`.

After that an unattended run logs in from the cached session in about a second, with `steamcmd +runscript <file>` and this file:

```text
@NoPromptForPassword 1
@ShutdownOnFailedCommand 1
login <account>
workshop_build_item "<path to the .vdf>"
quit
```

With these two settings the run logged in from the cached session and exited by itself. A run without a cached session, or with a failing command, was not tried. SteamCMD writes the account name and the SteamID in its own logs.

## Creating a hidden item

```text
"workshopitem"
{
    "appid"           "221100"
    "publishedfileid" "0"
    "contentfolder"   "<drive>:\\path\\to\\item"
    "visibility"      "2"
    "title"           "..."
    "description"     "..."
    "changenote"      "..."
}
```

`publishedfileid` 0 creates the item, and SteamCMD writes the new id back into the `.vdf`. The run printed `Create new workshop item ( PublishFileID <id>)`, `Uploading content...`, `Committing update...` and `Success.` in 13 seconds, with no `previewfile` and no Workshop legal agreement warning for that private item. `visibility` takes the Steamworks values 0 public, 1 friends only, 2 private and 3 unlisted; only 2 was used. Updating an item is the same `.vdf` with the item's id instead of 0 (not measured).
