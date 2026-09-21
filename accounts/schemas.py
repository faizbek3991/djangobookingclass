from datetime import datetime

from ninja import Schema
from pydantic import EmailStr


class UserOut(Schema):
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    is_staff: bool
    is_active: bool
    date_joined: datetime


class LoginIn(Schema):
    username: str
    password: str


class SignupIn(Schema):
    username: str
    email: EmailStr
    password: str
    first_name: str = ""
    last_name: str = ""


class AdminUserCreateIn(Schema):
    username: str
    email: EmailStr
    password: str
    first_name: str = ""
    last_name: str = ""
    is_staff: bool = False
    is_active: bool = True


class AdminUserUpdateIn(Schema):
    username: str
    email: EmailStr
    first_name: str = ""
    last_name: str = ""
    is_staff: bool = False
    is_active: bool = True


class MessageOut(Schema):
    detail: str
