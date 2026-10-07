from django.shortcuts import get_object_or_404, render
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView

from resources_app.models import LearningResource
from restapp.models import Category, Menu
from restapp.serializers import CategorySerializer, MenuSerializer

PROJECT_NAME = 'HiiT Student Course Management & Resource Portal'


def portal_home(request):
    course_cards = [
        {'title': 'Web Development', 'category': 'Frontend', 'instructor': 'Mr. Adebayo', 'students': 42},
        {'title': 'Database Systems', 'category': 'Backend', 'instructor': 'Mrs. Okafor', 'students': 38},
        {'title': 'Mobile App Design', 'category': 'UI/UX', 'instructor': 'Mr. Isah', 'students': 26},
    ]
    resources = LearningResource.objects.select_related('author').order_by('-created_at')[:3]
    context = {
        'project_name': PROJECT_NAME,
        'course_cards': course_cards,
        'resources': resources,
        'student_count': 640,
        'course_count': 12,
        'resource_count': resources.count(),
    }
    return render(request, 'restapp/home.html', context)


def portal_dashboard(request):
    context = {'project_name': PROJECT_NAME, 'student_count': 640, 'course_count': 12}
    return render(request, 'restapp/dashboard.html', context)


@api_view(['GET'])
def api_root(request):
    return Response(
        {
            'project': PROJECT_NAME,
            'message': 'Welcome to the API root.',
            'endpoints': {
                'categories': '/categories/',
                'menus': '/menus/',
                'resources': '/resources/',
            },
        },
        status=status.HTTP_200_OK,
    )


@api_view(['GET', 'POST'])
def category_list(request):
    if request.method == 'GET':
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    serializer = CategorySerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CategoryListView(APIView):
    def get(self, request, pk=None):
        if pk is not None:
            category = get_object_or_404(Category, pk=pk)
            serializer = CategorySerializer(category)
            return Response(serializer.data, status=status.HTTP_200_OK)

        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    'details': 'Category created successfully',
                    'data': serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        serializer = CategorySerializer(category, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    'details': f'Category {pk} updated successfully',
                    'data': serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        serializer = CategorySerializer(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    'details': f'Category {pk} updated successfully',
                    'data': serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk=None):
        if pk is not None:
            category = get_object_or_404(Category, pk=pk)
            category.delete()
            return Response(
                {'details': f'Category {pk} deleted successfully'},
                status=status.HTTP_204_NO_CONTENT,
            )

        Category.objects.all().delete()
        return Response(
            {'details': 'All categories deleted successfully'},
            status=status.HTTP_204_NO_CONTENT,
        )


@api_view(['GET', 'POST'])
def menu_list(request):
    if request.method == 'GET':
        menus = Menu.objects.all()
        serializer = MenuSerializer(menus, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    serializer = MenuSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MenuListView(APIView):
    def get(self, request, pk=None):
        if pk is not None:
            menu = get_object_or_404(Menu, pk=pk)
            serializer = MenuSerializer(menu)
            return Response(serializer.data, status=status.HTTP_200_OK)

        menus = Menu.objects.all()
        serializer = MenuSerializer(menus, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = MenuSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    'details': 'Menu created successfully',
                    'data': serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, pk):
        menu = get_object_or_404(Menu, pk=pk)
        serializer = MenuSerializer(menu, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    'details': f'Menu {pk} updated successfully',
                    'data': serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk=None):
        if pk is not None:
            menu = get_object_or_404(Menu, pk=pk)
            menu.delete()
            return Response(
                {'details': f'Menu {pk} deleted successfully'},
                status=status.HTTP_204_NO_CONTENT,
            )

        Menu.objects.all().delete()
        return Response(
            {'details': 'All menus deleted successfully'},
            status=status.HTTP_204_NO_CONTENT,
        )

    def patch(self, request, pk):
        menu = get_object_or_404(Menu, pk=pk)
        serializer = MenuSerializer(menu, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    'details': f'Menu {pk} updated successfully',
                    'data': serializer.data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
