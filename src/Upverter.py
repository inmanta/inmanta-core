'''
Created on May 30, 2016

@author: wouter
'''

import ruamel.yaml
import os


def rewrite(out):
    out = out.replace("impera.io", "inmanta.com")
    out = out.replace("Impera", "Inmanta")
    return out


def run():
    with open("module.yml", "r") as fd:
        data = ruamel.yaml.load(fd.read(), ruamel.yaml.RoundTripLoader)

    if not "requires" in data:
        return

    requires = data["requires"]

    requires = [x for x in requires.keys()]
    data["requires"] = requires

    impstmt = ''.join(["\nimport %s" % x for x in requires if requires is not "std"])

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
                out = rewrite(out)
                with open(name, 'w') as modified:
                    modified.write(out)



if __name__ == '__main__':
    run()
