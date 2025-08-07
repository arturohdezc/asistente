{ pkgs }: {
  deps = [
    pkgs.python312
    pkgs.python312Packages.pip
    pkgs.python312Packages.setuptools
    pkgs.python312Packages.wheel
    
    # Core web framework
    pkgs.python312Packages.fastapi
    pkgs.python312Packages.uvicorn
    
    # Database
    pkgs.python312Packages.sqlalchemy
    pkgs.python312Packages.aiosqlite
    
    # Data validation
    pkgs.python312Packages.pydantic
    pkgs.python312Packages.pydantic-settings
    
    # HTTP client
    pkgs.python312Packages.httpx
    
    # Google APIs
    pkgs.python312Packages.google-api-python-client
    pkgs.python312Packages.google-auth
    
    # Utilities
    pkgs.python312Packages.python-dotenv
    pkgs.python312Packages.pytz
    pkgs.python312Packages.structlog
    pkgs.python312Packages.prometheus-client
    
    # System dependencies
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