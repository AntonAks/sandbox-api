from pydantic import BaseModel


class LoginRequest(BaseModel):
    # Accept any string identifier — DB does the actual lookup.
    # EmailStr here would reject reserved TLDs (.local, .test, .invalid) that
    # are perfectly fine for internal/demo workshops.
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class CurrentUserResponse(BaseModel):
    user_id: int
    email: str
    display_name: str
