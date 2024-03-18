**************
Allocation V3
**************




Allocation V3 is a new framework that changes significantly compared to Allocation V2. It doesn't have
its own lifecycle stage anymore, but instead allocation happens during validation compile. The purpose is
the same as v2: filling up the read-only values of a service instance. The difference is that allocated attributes
are not set in the LSM unwrapping anymore, but instead in an implementation of the service, using plugins.

The advantage of this approach is that it simplifies greatly the process: you don't need anymore to write
allocator classes and all the required functions (needs_allocation, allocate, etc.). You also don't need to instantiate many
AllocationSpecV2 with your allocators inside. Instead, you just need to write one plugin per attribute
you want to allocate, it is less verbose and a much more straightforward approach.

Example
#######

The example below show you the use case where a single allocator is used the same way on both the
service instance and an embedded entity.

.. literalinclude:: allocation_sources/allocation_v3/allocation_v3_native.cf
    :linenos:
    :language: inmanta
    :lines: 1-53
    :caption: main.cf

.. literalinclude:: allocation_sources/allocation_v3/allocation_v3_native.py
    :linenos:
    :language: python
    :caption: plugins/__init__.py


Allocation V2 features
######################

Main differences between allocation v3 and v2 are:
 - Allocators are now defined in the plugins directory through the ``allocator()`` decorator.


V2 to V3 migration
##################

Allocation V2:
- In the model:
```
entity ValueService extends lsm::ServiceEntity:
    string                      name
    lsm::attribute_modifier     name__modifier="rw"
    int?                        first_value
    lsm::attribute_modifier     first_value__modifier="r"
end

index ValueService(name)
ValueService.embedded_values [0:] -- EmbeddedValue

entity EmbeddedValue extends lsm::EmbeddedEntity:
    string                      id
    lsm::attribute_modifier     id__modifier="rw"
    int?                        third_value
    lsm::attribute_modifier     third_value__modifier="r"
    string[]? __lsm_key_attributes = ["id"]
end

index EmbeddedValue(id)

implement ValueService using parents
implement EmbeddedValue using std::none

value_binding = lsm::ServiceEntityBinding(
    service_entity="allocatorv3_demo::ValueService",
    lifecycle=lsm::fsm::simple,
    service_entity_name="value-service",
    allocation_spec="value_allocation",
    strict_modifier_enforcement=true,
)

for assignment in lsm::all(value_binding):
    attributes = assignment["attributes"]

    service = ValueService(
        instance_id=assignment["id"],
        entity_binding=value_binding,
        name=attributes["name"],
        first_value=attributes["first_value"],
    )

    for embedded_value in attributes["embedded_values"]:
        service.embedded_values += EmbeddedValue(
            **embedded_value
        )
    end
end
```
- In the plugin:
```
class IntegerAllocator(AllocatorV2):

    def __init__(self, value: int, attribute: str) -> None:
        self.value = value
        self.attribute = dict_path.to_path(attribute)

    def needs_allocation(self, context: ContextV2) -> bool:
        try:
            if not context.get_instance().get(self.attribute):
                # Attribute not present
                return True
        except IndexError:
            return True

        return False

    def allocate(self, context: ContextV2) -> None:
        context.set_value(self.attribute, self.value)

AllocationSpecV2(
    "value_allocation",
    IntegerAllocator(value=1, attribute="first_value"),
    ForEach(
        item="item",
        in_list="embedded_values",
        identified_by="id",
        apply=[
            IntegerAllocator(
                value=3,
                attribute="third_value",
            ),
        ],
    ),
)
```

Allocation V3:
- In the model:
```
entity ValueServiceV3 extends lsm::ServiceEntity:
    string                      name
    lsm::attribute_modifier     name__modifier="rw"
    int?                        first_value
    lsm::attribute_modifier     first_value__modifier="r"
end

index ValueServiceV3(name)
ValueServiceV3.embedded_values [0:] -- EmbeddedValueV3

implementation set_first_value for ValueServiceV3:
    self.first_value = get_first_value(self, "first_value")
    for embedded_value in self.embedded_values:
        embedded_value.third_value = get_third_value(self, "embedded_values[id={{embedded_value.id}}].third_value")
    end
end

entity EmbeddedValueV3 extends lsm::EmbeddedEntity:
    string                      id
    lsm::attribute_modifier     id__modifier="rw"
    int?                        third_value
    lsm::attribute_modifier     third_value__modifier="r"
    string[]? __lsm_key_attributes = ["id"]
end

index EmbeddedValueV3(id)

implement ValueServiceV3 using parents, set_first_value
implement EmbeddedValueV3 using std::none

valuev3_binding = lsm::ServiceEntityBindingV2(
    service_entity="allocatorv3_demo::ValueServiceV3",
    lifecycle=lsm::fsm::simple,
    service_entity_name="value-service-v3",
    allocation_spec="value_allocation_v3",
    service_identity="name",
    service_identity_display_name="Name",
)

for assignment in lsm::all(valuev3_binding):
    attributes = assignment["attributes"]

    service = ValueServiceV3(
        instance_id=assignment["id"],
        entity_binding=valuev3_binding,
        name=attributes["name"],
    )

    for embedded_value in attributes["embedded_values"]:
        service.embedded_values += EmbeddedValueV3(
            id=embedded_value["id"],
        )
    end
end
```
- In the plugin:
```
@allocation_helpers.allocator()
def get_first_value(
    service: "lsm::ServiceEntity",
    attribute_path: "string",
) -> "int":
    return 1

@allocation_helpers.allocator()
def get_third_value(
    service: "lsm::ServiceEntity",
    attribute_path: "string",
) -> "int":
    return 3

allocation.AllocationSpecV2("value_allocation_v3")
```

As you can see in the example above, each plugin that you use to allocate must have an allocator decorator. \
The plugin also has 2 mandatory arguments, the `service instance` (usually self in the model) and the `attribute`
you want to allocate as a dict_path.


+--------------------------------+--------------------------------+
|                                |                                |
|.. literalinclude:: allocation_sources/allocation_v3/migration_example/v2_main.cf |.. literalinclude:: allocation_sources/allocation_v3/migration_example/v3_main.cf |
|                                |                                |
+--------------------------------+--------------------------------+
