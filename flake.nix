{
  description = "Spotipy Dashboard - Python Dev Shell";

  inputs = {
    nixpkgs.url = "https://flakehub.com/f/NixOS/nixpkgs/0.1";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs =
    {
      self,
      nixpkgs,
      flake-utils,
    }:
    flake-utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = import nixpkgs {
          inherit system;
          config.allowUnfree = true;
        };
      in
      {
        devShells.default = pkgs.mkShell rec {
          packages = with pkgs; [
            git
            python312
            postgresql
            libpqxx
            stdenv.cc.cc.lib
            stdenv.cc
            glib
            zlib
            openssl
            pkg-config
          ];

          env = {
            LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath packages;
          };

          shellHook = ''
            echo "Entering Spotipy Dashboard Dev Shell..."

            # ensure data directory exists for sqlite
            mkdir -p data

            export SOURCE_DATE_EPOCH=$(date +%s)

            if [ -d venv ]; then
              echo "Refreshing virtual environment symlinks..."
              rm -f venv/bin/python venv/bin/python3 venv/bin/python3.12
            fi

            python3.12 -m venv venv
            source venv/bin/activate

            # ensure python finds modules in src
            export PYTHONPATH=$PWD/src:$PYTHONPATH

            # install dependencies automatically
            echo "Checking dependencies..."
            pip install -q -r src/requirements.txt
            #pip install -q -r tests/requirements-test.txt

          '';
        };
      }
    );
}
