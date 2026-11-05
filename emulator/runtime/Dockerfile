FROM amd64/debian@sha256:80655819b0590fe800f7bd538dfb9c4b798b1107cc1091fc96b9484f527da8dc

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    libcapstone5 libgnutls30t64 libpng16-16t64 libpixman-1-0 zlib1g \
    libjpeg62-turbo libsasl2-2 libepoxy0 libnuma1 libglib2.0-0t64 \
    libspice-server1 libzstd1 libslirp0 libbpf1 libudev1 libusb-1.0-0 \
    libpmem1 libdaxctl1 libseccomp2 libfdt1 libncursesw6 libtinfo6 \
    libgbm1 libvulkan1 libvirglrenderer1 libcacard0 libusbredirparser1 \
    libnettle8t64 libgmp10 libhogweed6t64 libpam0g libfuse3-4 libaio1t64 \
    liburing2 libasound2t64 libsdl2-2.0-0 mesa-vulkan-drivers vulkan-tools \
    && dpkg-query -W -f='${binary:Package}\t${Version}\n' > /opt/runtime-packages.tsv \
    && rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y --no-install-recommends seabios ipxe-qemu qemu-system-data \
    && echo 'deb http://deb.debian.org/debian unstable main' > /etc/apt/sources.list.d/vmvga-virgl.list \
    && apt-get update \
    && cd /tmp && apt-get download libvirglrenderer1=1.3.0-1 \
    && dpkg-deb -x libvirglrenderer1_1.3.0-1_amd64.deb /opt/virgl13 \
    && sha256sum libvirglrenderer1_1.3.0-1_amd64.deb > /opt/virgl13-package.sha256 \
    && dpkg-deb -f libvirglrenderer1_1.3.0-1_amd64.deb > /opt/virgl13-package.control \
    && rm /etc/apt/sources.list.d/vmvga-virgl.list /tmp/libvirglrenderer1_1.3.0-1_amd64.deb \
    && dpkg-query -W -f='${binary:Package}\t${Version}\n' > /opt/runtime-packages.tsv \
    && rm -rf /var/lib/apt/lists/*

ENV LD_LIBRARY_PATH=/opt/virgl13/usr/lib/x86_64-linux-gnu
COPY qemu-system-x86_64 /opt/vmvga/qemu-system-x86_64
RUN echo 'ce36d097fd0954ba64462decd0b6ffc2d5448dcb843b76f3c535bfa790c21599  /opt/vmvga/qemu-system-x86_64' | sha256sum -c - \
    && chmod 0755 /opt/vmvga/qemu-system-x86_64 \
    && /opt/vmvga/qemu-system-x86_64 --version

ENV SDL_VIDEODRIVER=dummy
ENV XDG_RUNTIME_DIR=/tmp
RUN ln -s ../seabios/bios-256k.bin /usr/share/qemu/bios-256k.bin \
    && ln -s ../seabios/bios.bin /usr/share/qemu/bios.bin \
    && ln -s ../seabios/vgabios-vmware.bin /usr/share/qemu/vgabios-vmware.bin
ENTRYPOINT ["/opt/vmvga/qemu-system-x86_64"]
