def check_training_required(folder):
    for file in folder.files.all():
        if not hasattr(file, "ai_processed"):
            return True
    return False
