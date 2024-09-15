from pydantic import BaseModel, ConfigDict


class MyBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        defer_build=True,
        use_attribute_docstrings=True,
    )
