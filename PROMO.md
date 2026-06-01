# Promo kit

Reusable copy for sharing zenvision-studio / zenvision-linux. The hook: **this is
the first open-source Linux support for the ASUS ZenVision lid OLED** — protocol
reverse-engineered from scratch, plus a full app with audio-reactive visualisers.

Links:
- App: https://github.com/tarpediem/zenvision-studio
- Driver + protocol: https://github.com/tarpediem/zenvision-linux

## The one-liner

> Reverse-engineered the undocumented OLED in my ASUS Zenbook's lid and built a
> beat-reactive VJ rig on it — Linux driver + app, MIT.

## Best asset

A short phone video of the **physical lid screen** running plasma / katakana
Matrix / kaleidoscope while music plays (the VU / Layout-VJ reacting). That sells
it far better than the rendered GIF. 20–30 s, lid open, good lighting.

## Where to post (by impact)

1. **asus-linux** (Discord + the `asus-linux/reverse-engineering` GitLab) — the
   folks behind `asusctl`. Friendly, relevant, may relay/link it.
2. **r/ZenBook** + **r/ASUS** — owners of this exact machine (UX5401ZAS).
3. **r/unixporn** — the VJ visuals on the lid (needs the real-screen video).
4. **Hacker News — Show HN** — the RE story + driver + app.
5. **r/linux**, **r/linuxhardware**, **Mastodon** (#Linux #demoscene), and a tip
   to **Phoronix** (they cover Linux hardware reverse-engineering).

## Drafts

### Show HN
**Title:** Show HN: I reverse-engineered my ASUS Zenbook's lid OLED and built a VJ rig on it

The Zenbook 14X OLED Space Edition (UX5401ZAS) has a 256×64 OLED in the lid
("ZenVision") that only ASUS's Windows app could drive. I dumped MyASUS,
decompiled the USB transport with Ghidra and recovered the protocol, then wrote a
Linux userspace driver and an app: live applets (clock, system stats, MPRIS
now-playing) and audio-reactive visualisers (plasma, tunnel, kaleidoscope, fire,
katakana Matrix rain, metaballs…), a drag-and-drop zone layout editor, a
stylus-friendly frame editor, and a beat-synced auto-VJ. No Linux support existed
before. Protocol + driver and the app are linked below. MIT.

### r/unixporn
**Title:** [Hardware] Reverse-engineered my Zenbook's lid OLED — now it's a beat-reactive VJ screen on Linux

(Attach the real-screen video. Mention distro/WM in a comment per sub rules.)

### asus-linux (Discord / issue)
Owner of a UX5401ZAS here. The lid "ZenVision" OLED (USB `0b05:8835`, Nuvoton
M480) had zero Linux support, so I reverse-engineered the protocol (Ghidra on
MyASUS) and documented it, plus built a userspace driver and an app (applets +
audio visualisers). Repos and a protocol doc below — happy to help anyone porting
to other ASUS lid panels, and would love a link from the RE repo.

### r/ZenBook / r/ASUS
Got the lid OLED working on Linux (UX5401ZAS): clock, CPU/RAM, now-playing, and
audio-reactive visualisers. ASUS only ships a Windows app, so I reverse-engineered
the protocol. Open-source, MIT. [links]

## Phoronix tip (short email / submit form)

Subject: First open-source Linux support for the ASUS ZenVision lid OLED

Hi — thought this might interest your readers: the secondary OLED in the lid of
the ASUS Zenbook 14X OLED Space Edition ("ZenVision", USB 0b05:8835) had no Linux
support. I reverse-engineered the USB protocol (decompiled the MyASUS transport
with Ghidra) and released a documented protocol + a userspace driver, plus an app
with live applets and audio-reactive demoscene visualisers and a beat-synced
auto-VJ. Both MIT.

- Driver + protocol: https://github.com/tarpediem/zenvision-linux
- App: https://github.com/tarpediem/zenvision-studio

Happy to answer questions. Thanks!
