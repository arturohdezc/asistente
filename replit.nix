{ pkgs }: {
  deps = [
    pkgs.python312
    pkgs.python312Packages.pip
    pkgs.python312Packages.setuptools
    pkgs.python312Packages.wheel
  ];
  env = {
    PYTHON_LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
      # Needed for pandas / numpy
      pkgs.stdenv.cc.cc.lib
      pkgs.zlib
      # Needed for pygame
      pkgs.glib
      # Needed for matplotlib
      pkgs.xorg.libX11
    ];
    PYTHONHOME = "${pkgs.python312}";
    PYTHONBIN = "${pkgs.python312}/bin/python3.12";
    LANG = "en_US.UTF-8";
  };
}