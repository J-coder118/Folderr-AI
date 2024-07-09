from django import template
register = template.Library()
from filemanager.models import Folder, File, StickyNote, Task

@register.simple_tag
def root_folders():
    folders =Folder.objects.filter(is_root=True).count() 
    return folders if folders else 0

@register.simple_tag
def sub_folders():
    folders = Folder.objects.filter(is_root=False).count()
    return folders if folders else 0

@register.simple_tag
def files_total():
    files = File.objects.all().count() 
    return  files if files else 0

@register.simple_tag
def images_total():
    images = File.objects.exclude(file__icontains='.pdf').count()
    return images if images else 0

@register.simple_tag
def pdfs_total():
    pdfs = File.objects.filter(file__icontains='.pdf').count()
    return pdfs if pdfs else 0

@register.simple_tag
def sticky_notes_total():
    sticky_notes = StickyNote.objects.all().count()
    return sticky_notes if sticky_notes else 0

@register.simple_tag
def tasks_total():
    tags = Task.objects.all().count()
    return tags if tags else 0