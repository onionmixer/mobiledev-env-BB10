#!/usr/bin/env bash
set -eo pipefail
export QNX_CONFIGURATION=/tmp/qnx
mkdir -p "$QNX_CONFIGURATION"
export MAKEFLAGS="-I$QNX_TARGET/usr/include"
if [[ "${BB10_BUILD_TARGET:-device}" == simulator ]]; then
    export CPUVARDIR=x86
    BB10_SPEC=blackberry-x86-qcc
    BB10_QMAKE_CONFIG=simulator
    BB10_VARIANT=o-g
    BB10_BAR_CONFIGURATION=Simulator-Debug
    BB10_BAR_NAME=HelloCascades-simulator-unsigned.bar
else
    BB10_SPEC=blackberry-armv7le-qcc
    BB10_QMAKE_CONFIG=device
    BB10_VARIANT=o.le-v7-g
    BB10_BAR_CONFIGURATION=Device-Debug
    BB10_BAR_NAME=HelloCascades-unsigned.bar
fi

case "$1" in
    doctor)
        cd /tmp
        BB10_QCC_TARGETS="$(qcc -V 2>&1)"
        echo "$BB10_QCC_TARGETS"
        [[ "$BB10_QCC_TARGETS" == *gcc_ntoarmv7le* ]]
        qmake -v
        java -version
        blackberry-nativepackager -version
        ;;
    build)
        # qmake/qcc use 32-bit stat/readdir. Staging on tmpfs avoids inode
        # overflow on the host's XFS volume; don't build on the bind mount.
        mkdir -p /tmp/project
        cp -R /input/. /tmp/project/
        cd /tmp/project
        qmake -spec "$BB10_SPEC" HelloCascades.pro \
            "CONFIG+=$BB10_QMAKE_CONFIG" CONFIG+=debug CONFIG-=release
        make -j "${2:-4}"
        cp "$BB10_VARIANT/HelloCascades" /output/HelloCascades
        ;;
    package)
        mkdir -p /tmp/package
        cp -R /input/assets /tmp/package/
        cp /input/bar-descriptor.xml /tmp/package/
        cp /output/HelloCascades /tmp/package/
        cd /tmp/package
        blackberry-nativepackager -package "$BB10_BAR_NAME" \
            -devMode -platformVersion 10.3.1.0 \
            -configuration "$BB10_BAR_CONFIGURATION" bar-descriptor.xml
        cp "$BB10_BAR_NAME" /output/
        ;;
    deploy)
        cd /tmp
        [[ -n "${BB10_DEVICE_HOST:-}" ]]
        BB10_DEPLOY_ARGS=(-installApp -device "$BB10_DEVICE_HOST")
        if [[ -n "${BB10_DEVICE_PASSWORD:-}" ]]; then
            BB10_DEPLOY_ARGS+=(-password "$BB10_DEVICE_PASSWORD")
        fi
        if [[ "${BB10_BUILD_TARGET:-device}" == simulator ]]; then
            BB10_DEPLOY_ARGS+=(-launchApp)
        fi
        exec blackberry-deploy "${BB10_DEPLOY_ARGS[@]}" /output/deploy.bar
        ;;
    *) echo "Unknown container task" >&2; exit 2 ;;
esac
