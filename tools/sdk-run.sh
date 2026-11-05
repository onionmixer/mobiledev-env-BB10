#!/usr/bin/env bash
set -eo pipefail
BB10_WORKSPACE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "$BB10_WORKSPACE/config/local.env" ]]; then
    source "$BB10_WORKSPACE/config/local.env"
fi
export BB10_SDK_ROOT="${BB10_SDK_ROOT:-$BB10_WORKSPACE/sdk/bbndk}"
export QNX_HOST="$BB10_SDK_ROOT/host_10_3_1_12/linux/x86"
export QNX_TARGET="$BB10_SDK_ROOT/target_10_3_1_995/qnx6"
export QNX_CONFIGURATION="$BB10_WORKSPACE/.cache/qnx"
export QDE="$BB10_SDK_ROOT"
export CPUVARDIR="${BB10_CPUVARDIR:-armle-v7}"
export MAKEFLAGS="-I$QNX_TARGET/usr/include"
export LD_LIBRARY_PATH="$QNX_HOST/usr/lib:$QNX_TARGET/../linux/x86/usr/lib/qt4/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export QT_PLUGIN_PATH="$QNX_TARGET/../linux/x86/usr/lib/qt4/plugins"
export QT_LIB_PATH="$QNX_TARGET/../linux/x86/usr/lib/qt4/lib"
export PATH="$QNX_HOST/usr/bin:$QNX_CONFIGURATION/bin:$PATH"
if [[ -z "${BB10_JAVA_HOME:-}" && -x /usr/lib/jvm/java-8-openjdk-amd64/bin/java ]]; then
    BB10_JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64
fi
if [[ -n "${BB10_JAVA_HOME:-}" ]]; then
    export JAVA_HOME="$BB10_JAVA_HOME"
    export PATH="$JAVA_HOME/bin:$PATH"
fi
mkdir -p "$QNX_CONFIGURATION"
if [[ ! -x "$QNX_HOST/usr/bin/qcc" ]]; then
    echo "BB10 SDK missing: $QNX_HOST/usr/bin/qcc. Run npm run setup:sdk." >&2
    exit 2
fi
exec "$@"
