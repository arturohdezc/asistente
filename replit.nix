{ pkgs }: {
  deps = [
    pkgs.python312
    pkgs.python312Packages.pip
    pkgs.python312Packages.setuptools
    pkgs.python312Packages.wheel
    pkgs.sqlite
    pkgs.openssl
    pkgs.pkg-config
    pkgs.gcc
    pkgs.libc
  ];
  
  env = {
    PYTHON_LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
      pkgs.stdenv.cc.cc.lib
      pkgs.zlib
      pkgs.glibc
      pkgs.sqlite
      pkgs.openssl
    ];
    PYTHONHOME = "${pkgs.python312}";
    PYTHONPATH = "${pkgs.python312}/lib/python3.12/site-packages";
  };
}