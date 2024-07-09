from core.models import User
from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from filemanager.models import File, Folder, StickyNote


class UserCreationForm(forms.ModelForm):
    """A form for creating new users. Includes all the required
    fields, plus a repeated password."""

    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(
        label="Password confirmation", widget=forms.PasswordInput
    )

    class Meta:
        model = User
        fields = ("email", "phone_number", "terms_agreed", "user_type")

    def clean_password2(self):
        # Check that the two password entries match
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        # Save the provided password in hashed format
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserChangeForm(forms.ModelForm):
    """A form for updating users. Includes all the fields on
    the user, but replaces the password field with admin's
    disabled password hash display field.
    """

    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
            "password",
            "phone_number",
            "is_active",
            "terms_agreed",
            "membership",
            "receipt_scans",
            "emails_received",
            "storage_bytes_used",
            "profile_complete",
            "user_type",
        )


class UserAdmin(BaseUserAdmin):
    # The forms to add and change user instances
    # form = UserChangeForm
    add_form = UserCreationForm

    # The fields to be used in displaying the User model.
    # These override the definitions on the base UserAdmin
    # that reference specific fields on auth.User.
    list_display = (
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "terms_agreed",
        "date_joined",
        "last_login",
        "root_folders",
        "sub_folders",
        "files",
        "sticky_notes",
        "tasks",
        "subscription",
    )
    list_filter = ("email",)
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "password",
                    "user_type",
                )
            },
        ),
        (
            "Personal info",
            {
                "fields": (
                    "phone_number",
                    "terms_agreed",
                    "otp",
                    "is_verified",
                    "membership",
                    "profile_complete",
                )
            },
        ),
        (
            "Resource usage",
            {
                "fields": (
                    "receipt_scans",
                    "emails_received",
                    "storage_bytes_used",
                )
            },
        ),
        # ('Permissions', {'fields': ()}),
    )
    # add_fieldsets is not a standard ModelAdmin attribute. UserAdmin
    # overrides get_fieldsets to use this attribute when creating a user.
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "phone_number",
                    "password1",
                    "password2",
                    "terms_agreed",
                    "user_type",
                ),
            },
        ),
    )
    search_fields = (
        "first_name",
        "last_name",
        "email",
    )
    ordering = (
        "first_name",
        "last_name",
        "email",
        "date_joined",
        "last_login",
    )
    filter_horizontal = ()

    def subscription(self, obj):
        return obj.get_membership_display()

    def root_folders(self, obj):
        root_folders = Folder.objects.filter(
            created_by=obj, is_root=True
        ).count()
        return root_folders

    root_folders.admin_order_field = "root_folders"

    def sub_folders(Self, obj):
        sub_folders = Folder.objects.filter(
            created_by=obj, is_root=False
        ).count()
        return sub_folders

    sub_folders.admin_order_field = "sub_folders"

    def files(self, obj):
        files = File.objects.filter(created_by=obj).count()
        return files

    files.admin_order_field = "files"

    def sticky_notes(self, obj):
        sticky_notes = StickyNote.objects.filter(created_by=obj).count()
        return sticky_notes

    sticky_notes.admin_order_field = "sticky_notes"

    def tasks(self, obj):
        sticky_notes = StickyNote.objects.filter(created_by=obj).count()
        return sticky_notes

    tasks.admin_order_field = "tasks"

    def get_queryset(self, request):
        return (
            super(UserAdmin, self)
            .get_queryset(
                request,
            )
            .annotate(
                root_folders=Count(
                    "folder__id", filter=Q(folder__is_root=True)
                ),
                sub_folders=Count(
                    "folder__id", filter=Q(folder__is_root=False)
                ),
                files=Count("file__id"),
                sticky_notes=Count("stickynote__id"),
                tasks=Count("task__id"),
            )
        )


# Now register the new UserAdmin...
admin.site.register(User, UserAdmin)
# ... and, since we're not using Django's built-in permissions,
# unregister the Group model from admin.
admin.site.unregister(Group)
