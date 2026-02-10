"""
This file is licensed under simplified BSD, unless stated otherwise.

Unless stated otherwise in the source file, this code is copyright 2010 David
Wolever <david@wolever.net>. All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

   1. Redistributions of source code must retain the above copyright notice,
   this list of conditions and the following disclaimer.

   2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY <COPYRIGHT HOLDER> ``AS IS'' AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL <COPYRIGHT HOLDER> OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The views and conclusions contained in the software and documentation are those
of the authors and should not be interpreted as representing official policies,
either expressed or implied, of David Wolever.
"""

import html
import os
import re
import shutil
import sys

from inmanta.vendor.pkg_resources import safe_name


def try_symlink(source, target):
    try:
        os.symlink(source, target)
    except OSError as e:
        if e.errno == 17:
            # ignore errors when the file exists
            return
        sys.stderr.write("ERROR linking %s to %s (skipping): %s\n" % (source, target, e))


def normalize_pep503(pkg_name):
    # As per https://www.python.org/dev/peps/pep-0503/#normalized-names
    return re.sub(r"[-_.]+", "-", pkg_name).lower()


def file_to_package(file, basedir=None):
    """Returns the package name for a given file, or raises an
    ``ValueError`` exception if the file name is
    not valid::

    >>> file_to_package("foo-1.2.3_rc1.tar.gz")
    ('foo', '1.2.3-rc1.tar.gz')
    >>> file_to_package("foo-bar-1.2.tgz")
    ('foo-bar', '1.2.tgz')
    >>> file_to_package("kafka-quixey-0.8.1-1.tar.gz")
    ('kafka-quixey', '0.8.1-1.tar.gz')
    >>> file_to_package("foo-bar-1.2-py27-none-any.whl")
    ('foo-bar', '1.2-py27-none-any.whl')
    >>> file_to_package("Cython-0.17.2-cp26-none-linux_x86_64.whl")
    ('Cython', '0.17.2-cp26-none-linux_x86_64.whl')
    >>> file_to_package("PyYAML-3.10-py2.7-macosx-10.7-x86_64.egg")
    ('PyYAML', '3.10-py2.7-macosx-10.7-x86_64.egg')
    >>> file_to_package("python_ldap-2.3.9-py2.7-macosx-10.3-fat.egg")
    ('python-ldap', '2.3.9-py2.7-macosx-10.3-fat.egg')
    >>> file_to_package("python_ldap-2.4.19-cp27-none-macosx_10_10_x86_64.whl")
    ('python-ldap', '2.4.19-cp27-none-macosx_10_10_x86_64.whl')
    >>> file_to_package("foo.whl")
    Traceback (most recent call last):
        ...
    ValueError: unexpected file name: 'foo.whl' (not in 'pkg-name-version.xxx' format)
    >>> file_to_package("foo.png")
    Traceback (most recent call last):
        ...
    ValueError: unexpected file name: 'foo.png' (not in 'pkg-name-version.xxx' format)
    """
    file = os.path.basename(file)
    file_ext = os.path.splitext(file)[1].lower()
    if file_ext == ".egg":
        raise Exception(".egg files are not supported")
    elif file_ext == ".whl":
        bits = file.rsplit("-", 4)
        split = (bits[0], "-".join(bits[1:]))
        to_safe_name = safe_name
        to_safe_rest = lambda x: x  # noqa: E731
    else:
        match = re.search(r"(?P<pkg>.*?)-(?P<rest>\d+.*)", file)
        if not match:
            raise ValueError(f"File {file} in directory {basedir} has invalid name")
        split = (match.group("pkg"), match.group("rest"))
        to_safe_name = safe_name
        to_safe_rest = safe_name

    if len(split) != 2 or not split[1]:
        raise ValueError(f"File {file} in directory {basedir} has invalid name")

    return (to_safe_name(split[0]), to_safe_rest(split[1]))


def dir2pi(pkgdir: str) -> None:
    if not os.path.isdir(pkgdir):
        raise ValueError("no such directory: %r" % (pkgdir,))
    pkgdirpath = lambda *x: os.path.join(pkgdir, *x)  # noqa: E731

    shutil.rmtree(pkgdirpath("simple"), ignore_errors=True)
    os.mkdir(pkgdirpath("simple"))
    pkg_index = "<html><head><title>Simple Index</title>" "<meta name='api-version' value='2' /></head><body>\n"

    processed_pkg = set()
    for file in os.listdir(pkgdir):
        pkg_filepath = os.path.join(pkgdir, file)
        if not os.path.isfile(pkg_filepath):
            continue
        pkg_basename = os.path.basename(file)
        if pkg_basename.startswith("."):
            continue

        pkg_name, pkg_rest = file_to_package(pkg_basename, pkgdir)

        pkg_dir_name = normalize_pep503(pkg_name)

        pkg_dir = pkgdirpath("simple", pkg_dir_name)
        if not os.path.exists(pkg_dir):
            os.mkdir(pkg_dir)

        symlink_target = os.path.join(pkg_dir, pkg_basename)
        symlink_source = os.path.join("../../", pkg_basename)
        if hasattr(os, "symlink"):
            try_symlink(symlink_source, symlink_target)
        else:
            shutil.copy2(pkg_filepath, symlink_target)

        if pkg_name not in processed_pkg:
            pkg_index += "<a href='%s/'>%s</a><br />\n" % (
                html.escape(pkg_dir_name),
                html.escape(pkg_name),
            )
            processed_pkg.add(pkg_name)

        with open(os.path.join(pkg_dir, "index.html"), "a") as fp:
            fp.write(
                "<a href='%(name)s'>%(name)s</a><br />\n"
                % {
                    "name": html.escape(pkg_basename),
                }
            )
    pkg_index += "</body></html>\n"

    with open(pkgdirpath("simple/index.html"), "w") as fp:
        fp.write(pkg_index)
