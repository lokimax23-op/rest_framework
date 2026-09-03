from django.urls import path
from . import views

urlpatterns = [
    path("categories/", views.category_list, name="categories"),  #[cite: 6]
    path(
        "categories2/", views.CategoryListView.as_view()
    ),  # List & Create[cite: 6]
    path(
        "categories/<int:pk>/", views.CategoryListView.as_view(), name="category"
    ),  # Detail view[cite: 6]
    path("menus/", views.menu_list, name="menus"),
]

