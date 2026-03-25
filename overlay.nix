final: prev: {
  rssTorrentAutomator = final.python3Packages.buildPythonApplication {
    pname = "rss-torrent-automator";
    version = "1.0";

    src = final.lib.cleanSourceWith {
      src = ./src;
      filter =
        path: type:
        let
          baseName = baseNameOf (toString path);
        in
        !(builtins.elem baseName [
          "venv"
          "__pycache__"
        ]);
    };

    format = "other";

    dependencies = with final.python3Packages; [
      feedparser
      paramiko
      regex
    ];

    makeWrapperArgs = [ "--prefix PYTHONPATH : $out/lib/rss-torrent-automator" ];

    installPhase = ''
      mkdir -p $out/lib/rss-torrent-automator $out/bin
      cp feeds.py torrents.py downloads.py settings.py variables.py \
        $out/lib/rss-torrent-automator/
      cp main.py $out/bin/rss-torrent-automator
      chmod +x $out/bin/rss-torrent-automator
    '';

    meta = {
      description = "Automates RSS feed monitoring and torrent management";
    };
  };
}
