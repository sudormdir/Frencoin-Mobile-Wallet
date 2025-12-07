import os
from glob import glob
from os.path import join

import sh
from pythonforandroid.logger import shprint
from pythonforandroid.recipe import Recipe
from pythonforandroid.util import current_directory


class KawpowRecipe(Recipe):
    """Build the kawpow C library + Python CFFI bindings for Android."""

    name = "kawpow"
    version = "0.9.4.4"

    # Canonical PyPI source tarball for kawpow
    url = (
        "https://files.pythonhosted.org/packages/source/k/"
        "kawpow/kawpow-{version}.tar.gz"
    )

    # Python + C toolchain with cffi
    depends = ["python3", "openssl", "cffi"]

    # Your existing patch that disables tests, etc.
    patches = [
        "./patches/disable-tests.patch",
        "./patches/android-link-libc++_shared.patch",
    ]

    def get_build_dir(self, arch_name):
        # arch_name is like "arm64-v8a"
        return join(
            self.get_build_container_dir(arch_name), f"{self.name}-{self.version}"
        )

    def _cmake_build_and_install(self, arch, build_dir, env):
        """
        Run CMake + make + install using the Android NDK toolchain.
        Installs libkawpow, libkeccak, etc. into an arch-specific prefix.
        """
        ndk_dir = self.ctx.ndk_dir
        toolchain_file = join(ndk_dir, "build", "cmake", "android.toolchain.cmake")

        # Make a private copy of env so we don't mutate the caller's
        env = env.copy()
        extra_noexcept = " -fno-exceptions -fno-rtti"
        env["CFLAGS"] = env.get("CFLAGS", "") + extra_noexcept
        env["CXXFLAGS"] = env.get("CXXFLAGS", "") + extra_noexcept

        install_prefix = join(build_dir, f".install-{arch.arch}")

        cmake = sh.Command("cmake")
        make = sh.Command("make")

        build_subdir = join(build_dir, f"build-android-{arch.arch}")
        os.makedirs(build_subdir, exist_ok=True)

        with current_directory(build_subdir):
            cm_args = [
                f"-DCMAKE_TOOLCHAIN_FILE={toolchain_file}",
                "-DCMAKE_BUILD_TYPE=Release",
                f"-DANDROID_ABI={arch.arch}",
                f"-DANDROID_PLATFORM=android-{self.ctx.ndk_api}",
                f"-DCMAKE_INSTALL_PREFIX={install_prefix}",
                # Tell CMake this is an Android cross-compile, not macOS
                "-DCMAKE_SYSTEM_NAME=Android",
                "-DKAWPOW_BUILD_TESTS=OFF",
                # source dir is one level up from build-android-*
                "..",
            ]
            shprint(cmake, *cm_args, _env=env)
            shprint(make, "-j4", _env=env)
            shprint(make, "install", _env=env)

        return install_prefix

    def _build_python_binding(self, arch, build_dir, install_prefix, env):
        """
        Build the CFFI Python binding _kawpow*.so for this arch and copy it,
        with the kawpow package, into the Android Python bundle.
        """
        include_dir = join(install_prefix, "include")
        lib_dir = join(install_prefix, "lib")

        # Start from p4a's env for this arch (already has CC/CXX/LDFLAGS)
        env = env.copy()
        cflags = env.get("CFLAGS", "")
        ldflags = env.get("LDFLAGS", "")
        cpath = env.get("CPATH", "")
        libpath = env.get("LIBRARY_PATH", "")

        env["CFLAGS"] = (
            f"{cflags} -I{include_dir} -I{self.ctx.python_recipe.include_root(arch.arch)}"
        )
        env["CPATH"] = f"{cpath} -I{include_dir}" if cpath else f"-I{include_dir}"
        env["LIBRARY_PATH"] = f"{libpath}:{lib_dir}" if libpath else lib_dir

        # Link against C++ runtime and target Python to resolve symbols at dlopen() time
        env["LDFLAGS"] = (
            f"{ldflags} -L{lib_dir} -lc++_shared -static-libgcc"
            f" -L{self.ctx.get_libs_dir(arch.arch)}"
            f" -L{join(self.ctx.bootstrap.build_dir, 'libs', arch.arch)}"
            f" -L{arch.ndk_lib_dir_versioned}"
            f" -L{self.ctx.python_recipe.link_root(arch.arch)}"
            f" -lpython{self.ctx.python_recipe.link_version}"
        )

        # Ensure hostpython sees only its own environment; avoid target site-packages
        buildlib = env.get("BUILDLIB_PATH")
        if buildlib:
            env["PYTHONPATH"] = buildlib
        else:
            env.pop("PYTHONPATH", None)

        # Where the Python bindings live in the cpp-kawpow tree
        py_bindings_dir = join(build_dir, "bindings", "python")
        # Choose Python interpreter for CFFI build: env P4A_CFFI_PY or fallback to system python3
        py_bin = os.environ.get("P4A_CFFI_PY", "python3")
        python_for_cffi = sh.Command(py_bin)
        print(f">>> [KAWPOW] Using {py_bin} for cffi build")

        # Let _build.py know we're doing the Android build
        env["KAWPOW_ANDROID_BUILD"] = "1"
        # Isolate from user site-packages so the build is reproducible
        env["PYTHONNOUSERSITE"] = "1"

        with current_directory(py_bindings_dir):
            # Build the CFFI module with selected Python, cross-compiling for Android using the NDK CC in env.
            print(f">>> [KAWPOW] Building CFFI extension with {py_bin}")
            shprint(python_for_cffi, "kawpow/_build.py", _env=env)

        # ---- Copy into the Android Python bundle ----
        site_packages = self.ctx.get_site_packages_dir(arch)
        kawpow_pkg_src = join(py_bindings_dir, "kawpow")
        kawpow_pkg_dst = join(site_packages, "kawpow")

        # 1) Copy the pure-Python package "kawpow" (with __init__.py, _build.py, etc.)
        if os.path.exists(kawpow_pkg_dst):
            shprint(sh.rm, "-rf", kawpow_pkg_dst)
        print(">>> [KAWPOW] Copying to site-packages:", site_packages)
        print(">>> [KAWPOW] kawpow_pkg_src:", kawpow_pkg_src)
        print(">>> [KAWPOW] kawpow_pkg_dst:", kawpow_pkg_dst)
        shprint(sh.cp, "-r", kawpow_pkg_src, site_packages)

        # 2) Copy the compiled extension _kawpow*.so
        so_candidates = glob(join(py_bindings_dir, "_kawpow*.so"))
        if not so_candidates:
            raise RuntimeError("kawpow recipe: _kawpow extension did not build")

        for so_path in so_candidates:
            # Make it importable as `from _kawpow import ffi, lib`
            shprint(sh.cp, so_path, site_packages)
            # Also drop a copy inside the kawpow package (not strictly required)
            shprint(sh.cp, so_path, kawpow_pkg_dst)

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)
        env["CXXFLAGS"] += " -fexceptions"  # Critical flag for C++ exceptions
        env["CFLAGS"] += " -fexceptions"
        return env

    def build_arch(self, arch):
        """
        Full build for one arch:
        1. CMake build/install of C libs
        2. CFFI build of _kawpow*.so
        3. Copy kawpow + _kawpow into app's site-packages
        """
        env = self.get_recipe_env(arch)
        build_dir = self.get_build_dir(arch.arch)
        install_prefix = self._cmake_build_and_install(arch, build_dir, env)
        self._build_python_binding(arch, build_dir, install_prefix, env)


recipe = KawpowRecipe()
