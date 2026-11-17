# Publishing a signed mod to the Steam Workshop (DayZ, appid 221100)

Signing a built PBO with DsUtils, the Workshop item folder, and publishing with the Publisher or SteamCMD.
The release texts (description, changelog, classname list) come from `/dayz-release-pack`.

Not yet checked on `P:\`: this is measured tool and Steam behaviour, not vanilla data.

Measured on 2026-11-12 on one Windows PC with the Steam client signed in:
signing a released PBO, creating a hidden Workshop item with SteamCMD, and what
a SteamCMD login does to the Steam client on the same machine. Updating an item
and the subscriber's side (the download, the `!Workshop` junction and
`meta.cpp`) were **not** measured.

## The item folder

    addons\<Mod>.pbo
    addons\<Mod>.pbo.<authority>.bisign
    keys\<authority>.bikey
    mod.cpp

The `.biprivatekey` never goes into the item or the repository.

Measured: signing with the DsUtils of DayZ Tools
(`Bin\DsUtils`): `DSCreateKey <authority>` writes the key pair,
`DSSignFile <authority>.biprivatekey <Mod>.pbo` writes the `.bisign` beside the
PBO, and `DSCheckSignatures <addons folder> <keys folder>` printed
`Signature ... is OK`. The `.bisign` is a separate file: the PBO had the same
sha256 before and after signing. The three tools write `.RPT` and `.mdmp`
files next to their own executable, so run a copy of them from a folder of
your own.

## Two ways to publish

| | Publisher (DayZ Tools) | SteamCMD |
|---|---|---|
| Session | The running Steam client's (inferred from its files) | Its own login with an account |
| Command line | None in DayZ Tools | `+workshop_build_item <vdf>` |
| On a machine where people play | No second login (inferred from its files, not measured) | Kicks the Steam client off if it logs in with the client's account (below) |

`Bin\Publisher\Publisher.exe`
(file version 1.0.240.639, signed by Bohemia Interactive) is a 32-bit WPF
application that reaches Steam through `steam_api.dll`, with
`steam_appid.txt` = 221100. Its strings include `SteamAPI_Init`,
`IsSteamRunning` and "Publisher requires that the Steam client is online".
DayZ Tools ships no `PublisherCmd` (the command-line publisher of Arma 3
Tools), and no command-line option shows in the Publisher's strings. This was
read from the installed files without running them.

Inferred from those strings: the Publisher publishes with the session of the
running client instead of logging in. Not measured, and neither is whether it
disturbs that session.

## SteamCMD

### Before any SteamCMD login on a machine where people play

Measured: a SteamCMD login with the
account that the Steam client has signed in on the same machine replaces the
client's session. In the same second as SteamCMD's `LogOnResponse` OK, the
client's `logs\connection_log.txt` recorded
`RecvMsgClientLoggedOff('Session Replaced')` and
`not auto reconnecting due to Session Replaced`. The client did not reconnect
by itself and stayed offline for 46 minutes, until the owner restarted it.
Meanwhile, the other test runs on that machine reported kick 49 in
`WaitAuthPlayerLoginState` on the joins they tried.
`HKCU\Software\Valve\Steam\ActiveProcess` did not change, so a registry
check misses it; the client's `connection_log.txt` shows it.

So, on a machine where people play: publish with the Publisher, or run
SteamCMD with that account only while the Steam client is closed and no game
is running, the first login included. A second account was not tried.

Inferred, not measured: any SteamCMD login with that account does the same,
`workshop_download_item` included.

### Login

Measured: download
`https://steamcdn-a.akamaihd.net/client/installer/steamcmd.zip` and check that
`Get-AuthenticodeSignature steamcmd.exe` reports `Valid` with a Valve signer
before running it. The first run updates itself (about 43 MB) and relaunches,
and the relaunched process lost a `+quit` given on the command line, so do the
first run by hand. The login is the account owner's, once: `login <account>`
and the password; the first attempt answered `Account Logon Denied` and asked
for the Steam Guard code; then `quit`. After that an unattended run logged in
from the cached session in about one second, with `steamcmd +runscript <file>`
and this file:

    @NoPromptForPassword 1
    @ShutdownOnFailedCommand 1
    login <account>
    workshop_build_item "<path to the .vdf>"
    quit

With these two settings that run logged in from the cached session and exited
by itself; a run without a cached session, or with a failing command, was not
tried. SteamCMD writes the account name and the SteamID in its own logs.

### Creating a hidden item

Measured: creating a hidden DayZ item:

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

`publishedfileid` 0 creates the item, and SteamCMD writes the new id back into
the `.vdf`. The run printed `Create new workshop item ( PublishFileID <id>)`,
`Uploading content...`, `Committing update...` and `Success.` in 13 s, with no
`previewfile` and no Workshop legal-agreement warning for that private item.
`visibility` takes the Steamworks values 0 public, 1 friends only, 2 private
and 3 unlisted; only 2 was used. Updating means the same `.vdf` with the
item's id instead of 0 (not measured).
