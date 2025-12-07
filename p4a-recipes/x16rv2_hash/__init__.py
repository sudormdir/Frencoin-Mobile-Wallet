from pythonforandroid.recipe import CompiledComponentsPythonRecipe


class X16Rv2HashRecipe(CompiledComponentsPythonRecipe):
    """
    Cross-compile the x16rv2_hash C extension from its sdist.
    """
    name = "x16rv2_hash"
    version = "1.0"  # from your tarball

    url = (
        "https://files.pythonhosted.org/packages/source/x/"
        "x16rv2_hash/x16rv2_hash-{version}.tar.gz"
    )

    depends = ["python3"]
    call_hostpython_via_targetpython = False


recipe = X16Rv2HashRecipe()
