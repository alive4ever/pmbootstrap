"""
Copyright 2018 Oliver Smith

This file is part of pmbootstrap.

pmbootstrap is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

pmbootstrap is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with pmbootstrap.  If not, see <http://www.gnu.org/licenses/>.
"""
import os
import sys
import glob
import pytest

# Import from parent directory
pmb_src = os.path.realpath(os.path.join(os.path.dirname(__file__) + "/.."))
sys.path.append(pmb_src)
import pmb.parse.apkindex
import pmb.parse
import pmb.helpers.logging


@pytest.fixture
def args(request):
    import pmb.parse
    sys.argv = ["pmbootstrap.py", "chroot"]
    args = pmb.parse.arguments()
    args.log = args.work + "/log_testsuite.txt"
    pmb.helpers.logging.init(args)
    request.addfinalizer(args.logfd.close)
    return args


def test_qt_versions(args):
    """
    Verify, that all postmarketOS qt5- package versions match with Alpine's
    qt5-qtbase version.
    """
    # Upstream version
    index = pmb.helpers.repo.alpine_apkindex_path(args, "community", "armhf")
    index_data = pmb.parse.apkindex.package(args, "qt5-qtbase",
                                            indexes=[index])
    pkgver_upstream = index_data["version"].split("-r")[0]

    # Iterate over our packages
    failed = []
    for path in glob.glob(args.aports + "/*/qt5-*/APKBUILD"):
        # Read the pkgver
        apkbuild = pmb.parse.apkbuild(args, path)
        pkgname = apkbuild["pkgname"]
        pkgver = apkbuild["pkgver"]

        # When we temporarily override packages from Alpine, we set the pkgver
        # to 9999 and _pkgver contains the real version (see #994).
        if pkgver == "9999":
            pkgver = apkbuild["_pkgver"]

        # Compare
        if pkgver == pkgver_upstream:
            continue
        failed.append(pkgname + ": " + pkgver + " != " +
                      pkgver_upstream)

    assert [] == failed


def test_aportgen_versions(args):
    """
    Verify that the packages generated by 'pmbootstrap aportgen' have
    the same version (pkgver *and* pkgrel!) as the upstream packages
    they are based on.
    """
    # Get Alpine's "main" repository APKINDEX path
    index = pmb.helpers.repo.alpine_apkindex_path(args, "main", "armhf")

    # Alpine packages and patterns for our derivatives
    map = {"binutils": "binutils-*",
           "busybox": "busybox-static-*",
           "gcc": "gcc-*",
           "musl": "musl-*"}

    # Iterate over Alpine packages
    failed = []
    generated = "# Automatically generated aport, do not edit!"
    for pkgname, pattern in map.items():
        # Upstream version
        index_data = pmb.parse.apkindex.package(args, pkgname,
                                                indexes=[index])
        version_upstream = index_data["version"]

        # Iterate over our packages
        for path in glob.glob(args.aports + "/*/" + pattern + "/APKBUILD"):
            # Skip non-aportgen APKBUILDs
            with open(path) as handle:
                if generated not in handle.read():
                    continue

            # Compare the version
            print("Checking " + path)
            apkbuild = pmb.parse.apkbuild(args, path)
            version = apkbuild["pkgver"] + "-r" + apkbuild["pkgrel"]
            if version != version_upstream:
                failed.append(apkbuild["pkgname"] + ": " + version +
                              " != " + version_upstream +
                              " (from " + pkgname + ")")
                continue

    assert [] == failed
