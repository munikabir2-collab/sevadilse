from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    phone: str | None = None
    is_provider: bool = False


class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    is_provider: bool

    class Config:
        from_attributes = True
