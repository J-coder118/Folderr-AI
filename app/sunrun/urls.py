from rest_framework import routers
from sunrun.views import (
    ChecklistViewset,
    JobNoteViewset,
    JobPhotoViewset,
    JobVideoViewset,
    JobViewset,
)

app_name = "sunrun"

router = routers.SimpleRouter()
router.register("checklists", ChecklistViewset)
router.register("jobs", JobViewset)
router.register("job-photos", JobPhotoViewset)
router.register("job-videos", JobVideoViewset)
router.register("job-notes", JobNoteViewset)
urlpatterns = router.urls
