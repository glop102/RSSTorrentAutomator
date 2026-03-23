final: prev: {
  rssTorrentAutomator = final.python3Packages.buildPythonApplication {
    pname = "rss-torrent-automator";
    version = "1.0";

    src = final.lib.cleanSourceWith {
      src = ./.;
      filter =
        path: type:
        let
          baseName = baseNameOf (toString path);
        in
        !(builtins.elem baseName [
          "venv"
          "__pycache__"
          "custom"
          "examples"
        ]);
    };

    format = "other";

    propagatedBuildInputs = with final.python3Packages; [
      feedparser
      paramiko
    ];

    installPhase = ''
      mkdir -p $out/lib/rss-torrent-automator $out/bin
      cp main.py feeds.py torrents.py downloads.py settings.py variables.py \
        $out/lib/rss-torrent-automator/
      makeWrapper ${final.python3}/bin/python3 $out/bin/rss-torrent-automator \
        --add-flags "$out/lib/rss-torrent-automator/main.py" \
        --set PYTHONPATH "$out/lib/rss-torrent-automator"
    '';

    meta = {
      description = "Automates RSS feed monitoring and torrent management";
    };
  };
}
