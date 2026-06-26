from pydantic import BaseModel, Field, model_validator


class ChatRequest(BaseModel):
    query: str | None = Field(default=None, min_length=1)
    message: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_prompt(self):
        if not self.query and not self.message:
            raise ValueError("Debes enviar 'query' o 'message'")
        return self

    @property
    def prompt(self) -> str:
        return self.query or self.message


class ChatResponse(BaseModel):
    response: str