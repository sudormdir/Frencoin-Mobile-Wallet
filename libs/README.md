Native libraries for libsecp256k1
=================================

This directory is used by Buildozer to include the **libsecp256k1** shared
libraries needed by Electrum‑Frencoin when running on Android.  At
runtime the wallet’s `ecc_fast.py` module will search for a file named
``libsecp256k1.so``.  Without this library the wallet cannot sign or
verify transactions.

To build these libraries yourself you need the Android NDK and the
``secp256k1`` source tree.  Follow the steps below on a Linux or macOS
host with the NDK installed.  You only need to do this once per
version of the library.  If you change the ``--enable`` flags or update
to a new version of ``secp256k1`` you must rebuild the libraries.

1. Clone the upstream **secp256k1** repository::

       git clone https://github.com/bitcoin-core/secp256k1.git
       cd secp256k1

2. Configure the build for Android.  You must cross‑compile the
   library once for each architecture you intend to support.  The
   commands below assume your NDK is installed in
   ``$ANDROID_NDK_ROOT`` and you want to target API 21.  Adjust
   ``TARGET`` and ``API`` as necessary.

   For **armeabi-v7a** (32‑bit ARM)::

       export ANDROID_NDK_ROOT=/path/to/android-ndk
       export TOOLCHAIN="$ANDROID_NDK_ROOT/toolchains/llvm/prebuilt/$(uname -s | tr '[:upper:]' '[:lower:]')-x86_64"
       export TARGET=armv7a-linux-androideabi
       export API=21
       export CC="$TOOLCHAIN/bin/${TARGET}${API}-clang"
       export AR="$TOOLCHAIN/bin/llvm-ar"
       export RANLIB="$TOOLCHAIN/bin/llvm-ranlib"
       ./autogen.sh
       ./configure \
         --host="$TARGET" \
         --enable-shared --disable-static \
         --enable-experimental --enable-module-recovery
       make -j$(nproc)
       cp src/.libs/libsecp256k1.so /path/to/frencoin_mobile_wallet/libs/armeabi-v7a/

   For **arm64-v8a** (64‑bit ARM)::

       make distclean
       export TARGET=aarch64-linux-android
       export CC="$TOOLCHAIN/bin/${TARGET}${API}-clang"
       ./configure \
         --host="$TARGET" \
         --enable-shared --disable-static \
         --enable-experimental --enable-module-recovery
       make -j$(nproc)
       cp src/.libs/libsecp256k1.so /path/to/frencoin_mobile_wallet/libs/arm64-v8a/

3. After copying the shared libraries into the appropriate
   ``libs/<abi>`` directories, Buildozer will automatically package
   them into your APK if you have added the ``android.add_libs_*``
   directives to your ``buildozer.spec`` (see below).

4. Rebuild your APK with::

       buildozer android clean
       buildozer android debug

The wallet should now be able to load ``libsecp256k1.so`` on Android.