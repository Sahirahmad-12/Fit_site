from django.urls import path
from . import views

urlpatterns = [
    path('subscribe/',   views.save_subscription,   name='push_subscribe'),
    path('unsubscribe/', views.delete_subscription, name='push_unsubscribe'),
]