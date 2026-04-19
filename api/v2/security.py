from typing import Optional, Any, Callable
from django.http import HttpRequest
from django.contrib.auth.models import User as DjangoUser
from ninja.errors import AuthorizationError
from ninja.security import SessionAuth
from common.utils import is_teacher


class UserPassesTestAuth(SessionAuth):
    """
    Django Ninja API authentication handler working similarly to the
    user_passes_test() decorator, allowing to specify a custom test
    function for user authentication.
    """

    def __init__(self, test_func: Callable[[DjangoUser], bool]):
        """
        Initialize the authentication handler with a custom authorization test.

        Args:
            test_func: A callable that accepts an authenticated User object and
                returns True if the user is authorized, False otherwise. This
                function is only invoked if the user is logged in.
        """
        super().__init__()
        self.test_func = test_func

    def authenticate(self, request: HttpRequest, key: Optional[str]) -> Optional[Any]:
        user = super().authenticate(request, key)
        if user and isinstance(user, DjangoUser):
            if self.test_func(user):
                return user
            raise AuthorizationError()
        return None


is_teacher_auth = UserPassesTestAuth(test_func=is_teacher)
