from django.apps import apps
from django.contrib import admin
from filemanager.models import AssetType, SuggestedField, SuggestedFolder


class SuggestedFolderInline(admin.StackedInline):
    model = SuggestedFolder
    fields = ("title",)


class SuggestedFieldInline(admin.StackedInline):
    model = SuggestedField
    fields = ("title", "placeholder", "has_camera_access")


class AssetTypeAdmin(admin.ModelAdmin):
    model = AssetType
    fields = ("title", "hidden")
    inlines = (
        SuggestedFieldInline,
        SuggestedFolderInline,
    )


admin.site.register(AssetType, AssetTypeAdmin)

models = apps.get_models()

for model in models:
    if "HelpTopic" not in str(model):
        try:
            admin.site.register(model)
        except admin.sites.AlreadyRegistered:
            pass


class FolderAdmin(admin.ModelAdmin):
    list_display = ["id", "folder"]
