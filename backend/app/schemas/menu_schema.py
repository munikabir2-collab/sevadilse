from pydantic import BaseModel, Field


class MenuItemCreate(BaseModel):
    name: str
    category: str | None = None
    description: str | None = None
    price: float = Field(gt=0)
    is_available: bool = True
    image_url: str | None = None


class MenuItemUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    description: str | None = None
    price: float | None = Field(default=None, gt=0)
    is_available: bool | None = None
    image_url: str | None = None


class MenuItemOut(BaseModel):
    id: int
    provider_id: int
    name: str
    category: str | None
    description: str | None
    price: float
    is_available: bool
    image_url: str | None

    class Config:
        from_attributes = True