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
