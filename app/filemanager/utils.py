from filemanager.models import Folder, Share


def get_created_or_shared_folder(
    user, folder_pk, include_subfolders=True
) -> Folder | None:
    try:
        folder = user.folder_set.get(pk=folder_pk)
    except Folder.DoesNotExist:
        try:
            share = user.receiver.get(folder__id=folder_pk)
            folder = share.folder
        except Share.DoesNotExist:
            if include_subfolders:
                try:
                    sub_folder = Folder.objects.get(pk=folder_pk)
                    try:
                        share = user.receiver.get(
                            folder__id=sub_folder.parent.id
                        )
                        folder = share.folder
                    except Share.DoesNotExist:
                        folder = None
                except Folder.DoesNotExist:
                    folder = None
            else:
                folder = None
    return folder
