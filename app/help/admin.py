from django.contrib import admin

from help.models import HelpTopic, HelpTopicImage


class HelpTopicImageInline(admin.StackedInline):
    model = HelpTopicImage


class HelpTopicAdmin(admin.ModelAdmin):
    model = HelpTopic
    inlines = (HelpTopicImageInline,)


admin.site.register(HelpTopic, HelpTopicAdmin)
