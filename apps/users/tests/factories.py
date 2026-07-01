"""factory_boy factories for the users app."""
import factory
from django.contrib.auth import get_user_model

from apps.users.constants import UserRole

User = get_user_model()

# Default password used across tests; satisfies the complexity validator.
DEFAULT_PASSWORD = "TestPass123!"


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        # Our ``password`` post_generation hook performs the save itself.
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    role = UserRole.USER
    is_active = True
    is_email_verified = True

    @factory.post_generation
    def password(self, create: bool, extracted: str | None, **kwargs) -> None:
        """Hash and persist the password (defaults to ``DEFAULT_PASSWORD``)."""
        self.set_password(extracted or DEFAULT_PASSWORD)
        if create:
            self.save()


class UnverifiedUserFactory(UserFactory):
    is_email_verified = False


class StaffUserFactory(UserFactory):
    is_staff = True
    is_superuser = True
    role = UserRole.ADMIN
