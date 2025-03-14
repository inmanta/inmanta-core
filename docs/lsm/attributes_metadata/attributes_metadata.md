# Attribute and entity metadata


This section describes the metadata fields that can be associated with service entities, embedded entities and its attributes
and how these metadata fields can be set in the model.


## Attribute description

### Definition

The attribute description metadata is useful to provide textual information about attributes. This text will be displayed in the
service catalog view of the web console.

### Usage

To add a description to an attribute, create a metadata attribute with type string and whose name is the attribute's name
extended with the suffix `__description`.


### Example

```inmanta
entity Interface :
    string interface_name string interface_name__description="The name of the interface"
end
```

A detailed example can be found {ref}`here <quickstart_orchestration_model>`.


## Attribute modifier

### Definition

Adding the attribute modifier metadata lets the compiler know if:

* This attribute should be provided by an end-user or set by the orchestrator.
* This attribute's value is allowed to change after creation.


### Usage


The modifier itself is defined like a regular attribute, with a few caveats:

* it should be of type lsm::attribute_modifier.
* its name should extend the decorated attribute's name with the suffix `__modifier`.
* its value should be one of the {ref}`supported values <supported_values>`.


### Example

```inmanta
entity Interface :
    string interface_name lsm::attribute_modifier interface_name__modifier="rw+"
end
```

A detailed example can be found {ref}`here <quickstart_orchestration_model>`.

### Supported values

* **r**: This attribute can only be set by an allocator.
* **rw**: This attribute can be set on service instantiation. It cannot be altered anymore afterwards.
* **rw+**: This attribute can be set freely during any phase of the lifecycle.


Attributes modifiers can also be specified on {ref}`relational attributes <attribute_modifiers_on_a_relationship>`.


## Annotations

### Definition

Annotations are key-value pairs that can be associated with an entity (service entity or embedded entity) or an attribute
(simple attribute or relational attribute). These annotations don't influence the behavior of LSM or the Inmanta Service
Orchestrator itself, but are intended to pass meta data to other components. For example, they can be used to pass on
visualization meta-data to the the web-console to improve the user-experience.

### Annotations on entities

Annotations can be attached to an entity using the `__annotations` attribute. This attribute has the type `dict` and requires a
default value that defines the annotations. Each key-value pair in the dictionary contains respectively the name and the value
of the annotation. The value of an annotation can be any of the simple types (string, float, int, bool), lists and dicts. Note:
These values are the default values of an attribute, therefore they must be constants and cannot include varables, attribute
access or plugins.

The example below illustrates how the annotation `annotation=value` can be set on on a service entity. Annotations can be set on
embedded entities in the same way.

```inmanta
entity Interface extends lsm::ServiceEntity:
    string interface_name dict __annotations = {"annotation": "value"}
end
```

### Annotations on simple attributes

Annotations can be attached to simple (non-relational) attributes by defining an attribute of type dict, with a name
`<attribute>__annotations`, where `<attribute>` is the name of the attribute the annotations belong to. This attribute needs a
default value containing the attributes. The values of the elements in the dictionary must be strings.

The example below shows how the annotation `annotation=value` is set on the attribute `interface_name`. Annotations can be set
on simple attributes of embedded entities in the same way.

```inmanta
entity Interface extends lsm::ServiceEntity:
    string interface_name dict interface_name__annotations = {"annotation": "value"}
end
```

### Annotations on relational attributes

Annotations can be attached to a relational attribute by replacing the `--` part of the relationship definition with an instance
of the `lsm::RelationAnnotations` entity. This entity has a dict attribute `annotations` that represents the annotations that
should be set on the relational attribute. The values of this dictionary must be strings. By convention the name of the
`lsm::RelationAnnotations` instance should be prefixed and suffixed with two underscores. This improves the readability of the
relationship definition.

The example below illustrates how the annotation `annotation=value` can be attached to the relational attribute `ports`.

```inmanta
entity Router extends lsm::ServiceEntity:
    string name
end

entity Port extends lsm::EmbeddedEntity:
    number id
end

__annotations__ = lsm::RelationAnnotations(
    annotations={"annotation": "value"}
) Router.ports [0:] __annotations__ Port._router [1]
```

### Documentation tabs

Annotations can be used to have the web console render the content of one or more attributes in a tab called *Documentation*.
This can be used to document and explain details of the service to the user based on information in the orchestration model. The
attribute value is set during a compile. For example, the following LSM service orchestrates container based labs and provides
an overview of all the different services and devices in the lab.

![documentation tab](documentation.png)

One or more attributes at the root level can be used and they are all rendered in the documentation tab. The documentation is
defined as follows:

```inmanta
entity Service extends lsm::ServiceBase:
    string documentation = "# Lab documentation"
    lsm::attribute_modifier documentation__modifier = "r"
    dict documentation__annotations = {
        "web_presentation": "documentation",
        "web_title": "Lab overview",
        "web_icon": "FaInfo",
    }
end
```

1. An attribute of type string needs to be defined. We recommend to give it a default value so that the tab is not empty when
   the documentation has not be generated yet by the compiler.
2. The attribute modifier must be `r` which means that is not defined by the user and only by the orchestrator.
3. Annotations are used to control how the attirbute is rednered in the web console:
   - `web_presentation` is set to `documentation` 
   - Optionally `web_title` is set to the title that is shown in the tab. This title is only used when multiple attributes are
     defined as documentation. This title will be used on the card that contains the content of this attribute.
   - Optionally `web_icon` specifies a font awsome icon name. This icon is also only used when multiple attributes are defined
     as documentation.

In the orchestrsation model a call to `lsm::update_read_only_attribute` is used to upload the content of the documentation tab. For example:

```inmanta
instance.documentation = lsm::update_read_only_attribute(
    instance,
    "documentation",
    value=std::template(
        "./documentation.md.j2",
        instance=instance,
    ),
)
```

The content of the attribute should be valid markdown. It also supports mermaid diagrams inside the markdown. For example the following 
documentation tab is generated in a template:

```markdown
```mermaid
    flowchart LR
    %%{init:{'flowchart':{'nodeSpacing': 20, 'rankSpacing': 10, 'padding': 5}}}%%
    classDef infra stroke:#4266f5, stroke-width:2px
    classDef service stroke:#42f54b, stroke-width:2px

    classDef attribute stroke:#ffffde, fill:#ffffde, color:#000
    router-east:::infra
subgraph router-east
router-east-ip:::attribute
router-east-ip[10.255.255.2]
router-east-ge-0/0/2:::infra
subgraph router-east-ge-0/0/2[ge-0/0/2]
router-east-ge-0/0/2-vlan2000:::infra
router-east-ge-0/0/2-vlan2000[vlan 2000]
end
end
router-west:::infra
subgraph router-west
router-west-ip:::attribute
router-west-ip[10.255.255.4]
router-west-ge-0/0/2:::infra
subgraph router-west-ge-0/0/2[ge-0/0/2]
router-west-ge-0/0/2-vlan2001:::infra
router-west-ge-0/0/2-vlan2001[vlan 2001]
end
end
l2connect:::service
l2-2000:::service
l2-2000[L2VPN termination: ep-0] --- l2connect[L2VPN: vpls-20000]
router-east-ge-0/0/2-vlan2000 --- l2-2000
l2-2001:::service
l2-2001[L2VPN termination: ep-1] --- l2connect[L2VPN: vpls-20000]
router-west-ge-0/0/2-vlan2001 --- l2-2001

\```

### Netbox links
├─ [router-east](http://172.25.139.95:8080/dcim/devices/?q=router-east)
&emsp; ├─ [ge-0/0/2.2000](http://172.25.139.95:8080/dcim/interfaces/?q=ge-0/0/2.2000&device=router-east)
├─ [router-west](http://172.25.139.95:8080/dcim/devices/?q=router-west)
&emsp; ├─ [ge-0/0/2.2001](http://172.25.139.95:8080/dcim/interfaces/?q=ge-0/0/2.2001&device=router-west)

```

And results in the following view:

![documentation with mermaid](mermaid.png)


### Suggested values
