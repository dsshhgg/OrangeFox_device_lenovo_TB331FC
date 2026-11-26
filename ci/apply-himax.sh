#!/usr/bin/env bash
# Verify the actual synced source before changing it and replay the same function
# from the same file that will subsequently be compiled by Android's build.
set -euo pipefail
ci=$(cd "$(dirname "$0")" && pwd)
cd "$1"
file=minuitwrp/events.cpp
printf 'Recovery revision: '; git rev-parse HEAD
echo "aeb84b62de7fd67472f853770b3d67ca87a5428fccc2c31eb6dadb01efca0a16  $file" | sha256sum -c -
git -c core.autocrlf=false apply --check "$ci/himax-touch.patch"
git -c core.autocrlf=false apply "$ci/himax-touch.patch"
echo "e61dfae53d252cff667b3dbed3b74fd18cddb890a6a58c5e012e2d961e7a42ef  $file" | sha256sum -c -
python3 "$ci/replay_vk.py" "$file" --himax-tests
