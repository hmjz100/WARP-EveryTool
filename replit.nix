{ pkgs }: {
    deps = [
        pkgs.wget
        pkgs.qrencode.bin
        pkgs.busybox
        pkgs.bashInteractive
        pkgs.man
    ];
}