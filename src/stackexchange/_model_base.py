from pydantic import BaseModel, ConfigDict


class MyBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_assignment=True,
        strict=True,
        revalidate_instances="always",
        defer_build=True,
        use_attribute_docstrings=True,
        # serialize_by_alias=True,  # v2.11
    )
