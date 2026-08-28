from django.urls import path
from . import views

urlpatterns = [
    path('categories/', views.category_list, name='category-list'), #[cite: 6]
    path("categories2/", views.CategoryListView.as_view(), name="category-list2"),  # [cite: 6]
    
]
    

