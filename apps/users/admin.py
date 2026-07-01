"""Django admin for the custom user model."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from apps.users.models import ApiKey

User = get_user_model()


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ("user", "masked", "is_active", "last_used_at", "created_at")
    list_filter = ("is_active",)
    search_fields = ("user__username", "user__email", "key")
    autocomplete_fields = ("user",)
    readonly_fields = ("id", "key", "created_at", "updated_at", "last_used_at")


class UserCreationFormEmail(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "first_name", "last_name")


class UserChangeFormEmail(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    add_form = UserCreationFormEmail
    form = UserChangeFormEmail
    model = User

    ordering = ("-created_at",)
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_email_verified",
        "is_active",
        "is_staff",
        "created_at",
    )
    list_filter = ("role", "is_active", "is_staff", "is_email_verified", "is_deleted")
    search_fields = ("username", "email", "first_name", "last_name")
    readonly_fields = ("id", "created_at", "updated_at", "last_login", "deleted_at")

    fieldsets = (
        (None, {"fields": ("id", "username", "email", "password")}),
        (_("Personal info"), {"fields": ("first_name", "last_name", "role")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_email_verified",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Important dates"), {"fields": ("last_login", "created_at", "updated_at")}),
        (_("Soft delete"), {"fields": ("is_deleted", "deleted_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "email", "first_name", "last_name", "password1", "password2"),
            },
        ),
    )
