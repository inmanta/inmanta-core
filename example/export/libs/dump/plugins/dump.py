from Imp.export import plugin_export

import os, shutil, errno, re, yaml 

@plugin_export("dump")
def export_to_puppet(options, scope, config):
    # start generating
    host_type = scope.get_variable("Host", ["std"]).value
    
    host_objects = {}
    for instance in host_type:
        host_objects[instance] = []
        
    for variable in scope.get_variables():
        variable.is_available(scope)
        native_type = variable.value
        if hasattr(native_type, "native") and native_type.native:
            for native_object in native_type:
                if hasattr(native_object, "host"):
                    host_objects[native_object.host].append(native_object)
                else:
                    pass
                    # TODO: error
                    
    for host, objects in host_objects.items():
        output_path = os.path.join(options.output, re.sub("[^\w]", "_", host.name))
        try:
            shutil.rmtree(output_path)
        except OSError:
            pass
        
        try:
            os.mkdir(output_path)
        except OSError:
            pass
        
        fd = open(os.path.join(output_path, "dump.txt"), "w+")
        for obj in objects:
            fd.write("%s\n" % obj)
            fd.write("=" * 80)
            fd.write("\n")

            for attribute in obj.__attributes__:
                value = getattr(obj, attribute)
                fd.write("%s = '%s'\n" % (attribute, value))

            fd.write("\n")
