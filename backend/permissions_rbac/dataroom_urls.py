from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .folder_rule_views import DataroomFolderRuleViewSet
from .dataroom_role_views import DataroomRoleOptionsView

router = DefaultRouter()
router.register(r'folder-access-rules', DataroomFolderRuleViewSet, basename='folder-access-rule')

urlpatterns = [
    path('datarooms/<str:dataroom_id>/role-options/', DataroomRoleOptionsView.as_view(), name='dataroom-role-options'),
    path('', include(router.urls)),
]
