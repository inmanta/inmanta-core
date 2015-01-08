from Imp.plugins.base import plugin

@plugin
def uppercase(in_string : "string") -> "string": 
    return in_string.upper()

