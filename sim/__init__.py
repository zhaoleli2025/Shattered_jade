"""Shattered Jade (碎玉) — M0 deterministic combat simulation.

Engine-agnostic core (DESIGN.md §7): plain data + pure-ish functions, no I/O,
seeded named RNG streams, command-pattern turn resolution. The web prototype
(prototype_web/game.js) is the reference implementation this port must match.
"""
