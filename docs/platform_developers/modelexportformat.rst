Model Export Format
========================




#. top level is a dict with one entry for each instance in the model
#. the key in this dict is the object reference handle
#. the value is the serialized instance
#. the serialized instance is a dict with three fields: type, attributes and relation.
#. type is the fully qualified name of the type
#. attributes is a dict, with as keys the names of the attributes and as values a dict with one entry.
#. An attribute can have one or more of tree keys: unknows, nones and values. The "values" entry has as value a list with the attribute values. 
	If any of the values is Unknown or None, it is removed from the values array and the index at which it was removed is recorded in respective the unknowns or nones value
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
 
