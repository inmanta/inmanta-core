'''
Created on May 30, 2016

@author: wouter
'''

import ruamel.yaml
import os


def run():
    with open("module.yml", "r") as fd:
        data = ruamel.yaml.load(fd.read(), ruamel.yaml.RoundTripLoader)

    if not "requires" in data:
        return

    requires = data["requires"]

    requires = [x for x in requires.keys()]
    data["requires"] = requires

    impstmt = ''.join(["import %s\n" % x for x in requires if requires is not "std"])

    with open("module.yml", "w") as fd:
        fd.write(ruamel.yaml.dump(data, Dumper=ruamel.yaml.RoundTripDumper))

    for dirpath, dirnames, files in os.walk("model"):
        for name in files:
            if name.lower().endswith("cf"):
                name = os.path.join(dirpath, name)
                with open(name, 'r') as original:
                    fdata = original.read()
                with open(name, 'w') as modified:
                    modified.write(impstmt + fdata)


if __name__ == '__main__':
    run()
