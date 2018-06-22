with import <nixpkgs> {};

stdenv.mkDerivation {
  name = "d3mEnv";
  buildInputs = [
    cairo
    cairo.dev
    icu
    libpng.dev
    libjpeg.dev
    lzma
    pcre
    readline
    zlib.dev

    python27Full
    python27Packages.virtualenv

    rEnv
  ];
  src = null;
  shellHook = ''
    # Allow the use of wheels.
    SOURCE_DATE_EPOCH=$(date +%s)

    # Add the local R libraries to the R library path.
    mkdir -p rlib
    export R_LIBS_SITE=$PWD/rlib:$R_LIBS_SITE

    # Put readline in the LD_LIBRARY_PATH.
    export LD_LIBRARY_PATH=${readline}/lib:${stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH

    # Augment PKG_CONFIG_PATH.
    export PKG_CONFIG_PATH=${cairo.dev}/lib/pkgconfig:${libpng.dev}/lib/pkgconfig:${libjpeg.dev}/lib/pkgconfig:${zlib.dev}/lib/pkgconfig:$PKG_CONFIG_PATH
  '';
}
