# Buildozer specification for the Frencoin mobile wallet
#
# This file controls how buildozer packages the Kivy application
# into an Android APK.  Buildozer will read this file when you run
# ``buildozer android debug`` or similar commands.  Adjust the
# settings as necessary for your environment.  See the Buildozer
# documentation for full details.

[app]
# (str) Title of your application
title = Frencoin Wallet
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# (str) Package name (no spaces).  This becomes part of the
# application’s Java package (e.g. org.frencoin.wallet).
package.name = frencoinwallet

# (str) Package domain (in reverse DNS notation).  Change this to
# something you control if you intend to publish on the Play Store.
package.domain = org.frencoin

# (str) Source code directory.  All files in this directory will be
# copied into the APK.  You normally leave this as ``.``.
source.dir = .

# (list) Extensions to include from the source directory.  Python
# sources, Kivy kv files and common image formats are included by
# default.
source.include_exts = py,png,jpg,kv,atlas,csv,json,txt

# (str) Application version.  Increment this when releasing a new
# version.
version = 0.1

p4a.local_recipes = ./p4a-recipes

# (list) Application requirements.  We specify Kivy and Python3.
#
# The Electrum‑Frencoin code itself is vendored into the
# project and does not need to be downloaded from PyPI.  Buildozer
# will package whatever is found inside the project directory.  If
# you vendor other dependencies you can list them here too.
requirements = python3,kivy,pyjnius,android,
    attrs,aiohttp,multidict,yarl,filetype,idna,
    propcache,aiohappyeyeballs,aiosignal,frozenlist,python_socks,aiorpcx,certifi,dnspython,
    async-timeout,bitstring,
    aiofiles,anyio,
    httpcore,httpx,
    pyaes,qrcode,
    setuptools,sniffio,trio,typing-extensions,
    websockets,Pillow,
    h11,outcome,sortedcontainers,multiformats,
    typing-validation,multiformats-config,bases,ipfs-car-decoder,
    unix-fs-exporter,hamt-sharding,bitmap-sparse-array,protobuf,
    dag-cbor,cffi,kawpow,x16r_hash,x16rv2_hash

icon.filename = assets/icon.png
android.icon = assets/icon.png

# Android backup - allows wallet data to survive device reset/migration
# IMPORTANT: Only safe because wallet files are encrypted with user's password
android.allow_backup = True

# (str) Orientation of the application.  We use portrait mode.
orientation = portrait

# (bool) Package the application in fullscreen mode.
fullscreen = 1

# (int) Logging level: 1 (error), 2 (warning), 3 (info), 4
# (debug).  Increase this if you need more verbose build logs.
log_level = 2

# (str) Extra shared libraries to copy into the APK for each
# supported ABI.  These point at the ``libsecp256k1.so`` files you
# compile using the instructions in ``libs/README.md``.  Buildozer
# will package whatever files are in these directories, so ensure
# that the architecture names match those listed in
# ``android.arch`` above.
android.add_libs_arm64_v8a = ./libs/arm64-v8a/libsecp256k1.so
android.add_libs_armeabi_v7a = ./libs/armeabi-v7a/libsecp256k1.so

# (str) Architectures to build for.  Common values include
# ``armeabi-v7a`` and ``arm64-v8a``.  Setting both produces two
# separate APKs.
android.arch = arm64-v8a

[buildozer]
# (str) Directory where buildozer stores its build cache.  By
# default this is hidden inside your home directory.  You can
# change it to speed up subsequent builds or to put it on a larger
# partition.
# build_dir = ./.buildozer
