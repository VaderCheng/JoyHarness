#!/bin/bash
# JoyHarness macOS launcher
# Double-click this file to start JoyHarness.
cd "$(dirname "$0")"
python3 src/main.py "$@"
