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
    email: str
    phone: str | None
    is_provider: bool
    is_admin: bool

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    provider_id: int | None = None
    is_provider: bool
    is_admin: bool

class CurrentUserOut(BaseModel):
    id: int
    name: str
    email: str
    phone: str | None
    is_provider: bool
    is_admin: bool

    class Config:
        from_attributes = True