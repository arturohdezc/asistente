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
    
    # Utilities
    pkgs.python312Packages.python-dotenv
    pkgs.python312Packages.structlog
    
    # System dependencies
    pkgs.sqlite
    pkgs.openssl
  ];
}