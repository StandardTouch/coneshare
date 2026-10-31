from django.urls import path

from .views import InviteSetPasswordView, InviteValidateView

urlpatterns = [
    path('invite/validate/', InviteValidateView.as_view(), name='invite_validate'),
    path('invite/set-password/', InviteSetPasswordView.as_view(), name='invite_set_password'),
]
