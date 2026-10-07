from django.urls import path

from .views import LearningResourceDetailView, LearningResourceListCreateView

app_name = 'resources_app'

urlpatterns = [
    path('', LearningResourceListCreateView.as_view(), name='resource-list'),
    path('<int:pk>/', LearningResourceDetailView.as_view(), name='resource-detail'),
]
