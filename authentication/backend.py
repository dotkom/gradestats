from django.contrib.auth.models import User
from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from mozilla_django_oidc.contrib.drf import OIDCAuthentication


def resolve_names(full_name: str):
    names = full_name.split(" ")
    if len(names) < 2:
        return None, None
    last_name = names.pop()
    first_name = " ".join(names)
    return first_name, last_name


class OIDCUserAuthenticationBackend(OIDCAuthenticationBackend):
    cache = {}
    def get_username(self, claims: dict):
        email: str = claims.get("email")
        username = email.split("@")[0]
        if not username or username == "":
            return super().create_user(claims)
        return username

    def create_user(self, claims: dict):
        user: User = super().create_user(claims)
        user.first_name, user.last_name = resolve_names(claims.get("name"))
        user.save()
        return user

    def update_user(self, user: User, claims: dict):
        user.first_name, user.last_name = resolve_names(claims.get("name"))
        user.username = self.get_username(claims)
        user.save()
        return user

    def get_userinfo(self, access_token, id_token, payload):
        print(access_token)
        print(id_token)
        print(payload)
        return super().get_userinfo(access_token, id_token, payload)


class OIDCUserAuthentication(OIDCAuthentication):
    pass
