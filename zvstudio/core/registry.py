"""Applet discovery: built-ins plus third-party plugins registered under the
``zvstudio.applets`` entry-point group."""
from __future__ import annotations

from importlib import metadata

from .applets.base import Applet
from .applets.clock import ClockApplet
from .applets.cycle import CycleApplet
from .applets.geo import CubeApplet, StarfieldApplet, TrianglesApplet
from .applets.logo import LogoApplet
from .applets.nowplaying import NowPlayingApplet
from .applets.player import PlayerApplet
from .applets.sysmon import SysmonApplet
from .applets.text import TextApplet
from .applets.viz import (
    KaleidoApplet,
    LissajousApplet,
    PlasmaApplet,
    ScopeApplet,
    TunnelApplet,
)
from .applets.vumeter import VuMeterApplet
from .applets.weather import WeatherApplet

BUILTIN = [
    ClockApplet, SysmonApplet, NowPlayingApplet, VuMeterApplet,
    PlasmaApplet, TunnelApplet, ScopeApplet, KaleidoApplet, LissajousApplet,
    TrianglesApplet, CubeApplet, StarfieldApplet, CycleApplet,
    LogoApplet, PlayerApplet, TextApplet, WeatherApplet,
]


def all_applets() -> dict[str, type[Applet]]:
    reg: dict[str, type[Applet]] = {c.meta.key: c for c in BUILTIN}
    try:
        for ep in metadata.entry_points(group="zvstudio.applets"):
            try:
                reg[ep.name] = ep.load()
            except Exception:
                pass
    except Exception:
        pass
    return reg


def get_applet(key: str) -> type[Applet] | None:
    return all_applets().get(key)
