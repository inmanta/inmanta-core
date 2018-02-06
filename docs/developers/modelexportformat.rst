Model Export Format
========================




#. top level is a dict with one entry for each instance in the model
#. the key in this dict is the object reference handle
#. the value is the serialized instance
#. the serialized instance is a dict with three fields: type, attributes and relation.
#. type is the fully qualified name of the type
#. attributes is a dict, with as keys the names of the attributes and as values a dict with one entry.This entry has key "values" and as value a list with the value of values (in case of [] type) of this attribute
#. relations is like attributes, but the list of values contains the reference handles to which this relations points 

Basic structure as pseudo jinja template 

.. code-block:: js+jinja

	{
	{% for instance in instances %}
	 '{{instance.handle}}':{
	 	"type":"{{instance.type.fqn}}",
	 	"attributes":[ 
	 		{% for attribute in instance.attributes %}
	 		"{{attribute.name}}": [ {{ attribute.values | join(",") }} ]
	 		{% endfor %}
	 	]
	 	"relations" : [
	 		{% for relation in instance.relations %}
	 		"{{relation.name}}": [ 
	 			{% for value in relation.values %}
	 				{{value.handle}}
	 			{% endfor %}
	 		]
	 		{% endfor %}
	 	]
	 	
	{% endif %}
	}  

Type Export Format
========================

.. automodule:: inmanta.model
   :members:
   :private-members:
 
