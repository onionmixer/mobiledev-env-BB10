#!/usr/bin/env bash
set -euo pipefail
BB10_AUDIO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../.." && pwd)"
BB10_AUDIO_OUT="$BB10_AUDIO_ROOT/emulator/evidence/audio-experiment"
BB10_AUDIO_STAGE="$(mktemp -d /tmp/bb10-ak4531.XXXXXX)"
trap 'rm -rf -- "$BB10_AUDIO_STAGE"' EXIT
mkdir -p "$BB10_AUDIO_OUT"
cp "$BB10_AUDIO_ROOT"/emulator/research/audio/*.[ch] "$BB10_AUDIO_STAGE/"
cc -std=c99 -Wall -Wextra -Werror "$BB10_AUDIO_STAGE/codec.c" "$BB10_AUDIO_STAGE/test_codec.c" -o "$BB10_AUDIO_STAGE/test_codec"
"$BB10_AUDIO_STAGE/test_codec"
cd "$BB10_AUDIO_STAGE"
bash "$BB10_AUDIO_ROOT/tools/sdk-run.sh" qcc -Vgcc_ntox86 -std=c99 -Wall -Wextra -fPIC -shared -Wl,-soname,deva-mixer-ak4531.so ak4531.c codec.c -o deva-mixer-ak4531.so
cp deva-mixer-ak4531.so "$BB10_AUDIO_OUT/"
sha256sum "$BB10_AUDIO_OUT/deva-mixer-ak4531.so"
