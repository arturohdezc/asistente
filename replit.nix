{ pkgs }: {
  deps = [
    pkgs.python312
    pkgs.python312Packages.pip
    pkgs.python312Packages.setuptools
    pkgs.python312Packages.wheel
    
    # System dependencies only - let pip handle Python packages
    pkgs.sqlite
    pkgs.openssl
    pkgs.pkg-config
    pkgs.gcc
    pkgs.libc
    pkgs.zlib
  ];
  
  env = {
    PYTHON_LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
      pkgs.stdenv.cc.cc.lib
      pkgs.zlib
      pkgs.glibc
      pkgs.sqlite
      pkgs.openssl
    ];
    PYTHONPATH = "$REPL_HOME/.pythonlibs/lib/python3.12/site-packages:$PYTHONPATH";
  };
}