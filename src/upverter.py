"""
    Copyright 2016 Inmanta

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

        http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

    Contact: code@inmanta.com
"""

import os

import ruamel.yaml
import subprocess


def rewrite(out):
    out = out.replace("Copyright 2015 Impera", "Copyright 2016 Inmanta")
    out = out.replace("    Contact: bart@impera.io", "    Contact: code@inmanta.com")
    out = out.replace("    Contect: bart@impera.io", "    Contact: code@inmanta.com")
    out = out.replace("    Contact: bart@inmanta.com", "    Contact: code@inmanta.com")
    out = out.replace("impera.io", "inmanta.com")
    out = out.replace("Impera", "Inmanta")
    out = out.replace("from impera", "from inmanta")
    out = out.replace("import impera", "import inmanta")
    return out


def run():
    with open("module.yml", "r") as fd:
        data = ruamel.yaml.load(fd.read(), ruamel.yaml.RoundTripLoader)

    data["author"] = "Inmanta <code@inmanta.com>"
    data["license"] = "Apache 2.0"
    if "source" in data:
        del data["source"]

    if "requires" in data:
        requires = data["requires"]

        requires = [x for x in requires.keys()]
        data["requires"] = requires

        impstmt = ''.join(["\nimport %s" % x for x in requires if x != "std"])

    with open("module.yml", "w") as fd:
        out = ruamel.yaml.dump(data, Dumper=ruamel.yaml.RoundTripDumper)
        out = rewrite(out)
        fd.write(out)

    for dirpath, dirnames, files in os.walk("model"):
        for name in files:
            if name.lower().endswith("cf"):
                name = os.path.join(dirpath, name)
                with open(name, 'r') as original:
                    fdata = original.read()
                parts = fdata.split("\"\"\"")
                if "ip::services" in fdata:
                    parts[2] = impstmt + "\nimport ip::services" + parts[2]
                else:
                    parts[2] = impstmt + parts[2]

                out = "\"\"\"".join(parts)
                out = rewrite(out)
                with open(name, 'w') as modified:
                    modified.write(out)

    for dirpath, dirnames, files in os.walk("plugins"):
        for name in files:
            if name.lower().endswith("py"):
                name = os.path.join(dirpath, name)
                with open(name, 'r') as original:
                    fdata = original.read()
                out = rewrite(fdata)
                with open(name, 'w') as modified:
                    modified.write(out)

    if not os.path.exists(".gitignore"):
        with open(".gitignore", "w+") as fd:
            fd.write("""*.swp
*.pyc
*~
            """)
    subprocess.check_call(["git", "add", ".gitignore"])

    with open(".gitlab-ci.yml", "w+") as fd:
            fd.write("""validate:
    image: fedora-inmanta
    tags:
        - docker
    script:
        - inmanta -vvv modules validate -r git@git.inmanta.com:modules/
    only:
        - tags
""")
    subprocess.check_call(["git", "add", ".gitlab-ci.yml"])


if __name__ == '__main__':
    run()
