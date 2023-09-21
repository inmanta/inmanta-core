# Running migration tool

## General notes about what the tool does:

------------------------------------------------------
Adds explicit None default to all Optional: (in v1 if no default was provided, None was implicitly provided)

```diff
-    resource_set: Optional[str]
+    resource_set: Optional[str] = None
```
------------------------------------------------------

Refactors config:

```diff
-    class Config:
-        # This comment gets lost in migration
-        extra = Extra.allow
+    model_config = ConfigDict(extra="allow")
```

⚠️ Comments get lost in migration

Some todos are added e.g.

```diff
+ # TODO[pydantic]: The following keys were removed: `fields`.
+ # Check https://docs.pydantic.dev/dev-v2/migration/#changes-to-config for more information.
```


------------------------------------------------------

Refactors validators:

```diff
-    @validator("current", "desired")
+    @field_validator("current", "desired")
+    @classmethod
     @classmethod
     def check_serializable(cls, v: Optional[Any]) -> Optional[Any]:
         """
```
⚠️ @classmethod decorator is added even if already present


The docs mentions the order of the decorators is important:

https://docs.pydantic.dev/2.3/usage/validators/:
```text
We recommend you use the @classmethod decorator on them below the @field_validator decorator to get proper type checking.
```

------------------------------------------------------



## Specific points of attention:

The following fixes are PoC grade i.e. not guaranteed to be correct:

- https://github.com/inmanta/inmanta-core/blob/ce19daf93564918a281c6ad44c1f2d3d906e851e/src/inmanta/data/model.py#L307

⬇

- https://github.com/inmanta/inmanta-core/blob/8d5c2c59aacf9218eab2293991d05b2140410219/src/inmanta/data/model.py#L276

------------------------------------------------------


- https://github.com/inmanta/inmanta-lsm/blob/f0ff765925a3e4fa8e2f322b333e1621cc61b42a/src/inmanta_lsm/model.py#L1885


⬇

- https://github.com/inmanta/inmanta-lsm/pull/1425/files#r1321729162

------------------------------------------------------

- https://github.com/inmanta/inmanta-core/blob/e134b55107d1091bfca2a17174f0379f7279d20d/src/inmanta/server/validate_filter.py#L125
see (https://docs.pydantic.dev/2.3/migration/#the-allow_reuse-keyword-argument-is-no-longer-necessary)

⬇

- https://github.com/inmanta/inmanta-core/pull/6463/files#r1321731415
------------------------------------------------------

- https://github.com/inmanta/inmanta-core/blob/ee659f653170b5b1c699a2c85e815db5991a1325/src/inmanta/module.py#L1225

⬇

- https://github.com/inmanta/inmanta-core/pull/6463/files#r1321732770

Change

```python
    _raw_parser: Type[YamlParser] = YamlParser
```
To:

```python
    @classmethod
    def _raw_parser_parse(cls, source: Union[str, TextIO]) -> Mapping[str, object]:
        return YamlParser.parse(source)
```


Because :

```sh

E       AttributeError: 'ModelPrivateAttr' object has no attribute 'parse'
attributes starting with underscore are converted into a "private attribute" which is not validated or even set during calls to __init__, model_validate
see https://docs.pydantic.dev/latest/usage/models/#private-model-attributes

```

------------------------------------------------------


- https://github.com/inmanta/inmanta-lsm/blob/3b960eb266a89313168b0def10695a70f8a45033/src/inmanta_lsm/model.py#L274

⬇

- https://github.com/inmanta/inmanta-lsm/pull/1425/files#r1321734333

add  `__get_pydantic_core_schema__` to Operation:

Because of :

```sh
  File "/home/hugo/.virtualenvs/pydanticv2poc/lib/python3.9/site-packages/pydantic/_internal/_generate_schema.py", line 694, in _generate_schema
    return self.match_type(obj)
  File "/home/hugo/.virtualenvs/pydanticv2poc/lib/python3.9/site-packages/pydantic/_internal/_generate_schema.py", line 781, in match_type
    return self._unknown_type_schema(obj)
  File "/home/hugo/.virtualenvs/pydanticv2poc/lib/python3.9/site-packages/pydantic/_internal/_generate_schema.py", line 377, in _unknown_type_schema
    raise PydanticSchemaGenerationError(
pydantic.errors.PydanticSchemaGenerationError: Unable to generate pydantic-core schema for <class 'inmanta_lsm.model.Operation'>. Set `arbitrary_types_allowed=True` in the model_config to ignore this error or implement `__get_pydantic_core_schema__` on your type to fully support it.

If you got this error by calling handler(<some type>) within `__get_pydantic_core_schema__` then you likely need to call `handler.generate_schema(<some type>)` since we do not call `__get_pydantic_core_schema__` on `<some type>` otherwise to avoid infinite recursion.

```

see: https://errors.pydantic.dev/2.3/u/schema-for-unknown-type

------------------------------------------------------


change to module.yml in lsm

compiler_version: 2023.3

To


compiler_version: "2023.3"

because of strict mode which is now enabled by default which disables auto casting from float to str


same for std: -> ugly hacked directly in core module.py Metadata.parse

## unions and strict mode 

Strict mode does no longer evaluate left to right which is actually what we want. However, in some places we rely on this
fact. For example the protocol test case. We pass an integer and we expect an integer back. However, when it is used in a get
call the value is passed as a string in the url, which per definition is a string.

## regex vs pattern

https://docs.pydantic.dev/2.3/migration/#patterns-regex-on-strings

We this for example in std::validate_type (could handle it there). pattern is a different regex dialect so it might not be
compatible.