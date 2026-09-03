from django.urls import path

from . import views

urlpatterns = [
    path('categories/', views.category_list, name='categories'),
    path('categories2/', views.CategoryListView.as_view(), name='categories2'),
    path('categories/<int:pk>/', views.CategoryListView.as_view(), name='category-detail'),
    path('menus/', views.menu_list, name='menus'),
    path('menus/<int:pk>/', views.MenuListView.as_view(), name='menu-detail'),
]

