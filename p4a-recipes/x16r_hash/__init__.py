from pythonforandroid.recipe import CompiledComponentsPythonRecipe


class X16rHashRecipe(CompiledComponentsPythonRecipe):
    """
    Cross-compile the x16r_hash C extension from its sdist.
    """
    name = "x16r_hash"
    version = "1.0.1"

    # canonical PyPI "source" URL; p4a will format {version}
    url = (
        "https://files.pythonhosted.org/packages/source/x/"
        "x16r_hash/x16r_hash-{version}.tar.gz"
    )

    # Make sure Python is built first, but nothing special besides that
    depends = ["python3"]
    call_hostpython_via_targetpython = False


recipe = X16rHashRecipe()
