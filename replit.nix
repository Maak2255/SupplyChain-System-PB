{ pkgs }:

pkgs.mkShell {
  buildInputs = [ pkgs.python3 pkgs.python3Packages.flask ];

  shellHook = ''
    export FLASK_APP=main.py
    export FLASK_RUN_PORT=80
  '';
}
