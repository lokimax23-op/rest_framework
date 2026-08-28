from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from restapp.models import Category
from restapp.serializers import CategorySerializer
from restapp.models import Category
from restapp.serializers import CategorySerializer
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response


# Ensure category_list is defined at the top level
@api_view(['GET', 'POST'])
def category_list(request):
    if request.method == 'GET':
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)

    if request.method == 'POST':
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)







class CategoryListView(APIView):
    # Handle GET requests (both list and single object by pk)
    def get(self, request, pk=None):
        if pk:
            category = get_object_or_404(Category, pk=pk)
            serializer = CategorySerializer(category)
            return Response(serializer.data, status=status.HTTP_200_OK)

        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(
                {
                    "details": "Category created successfully",
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

    # Handle DELETE requests (both single object by pk and bulk delete)
    def delete(self, request, pk=None):
        if pk:
            category = get_object_or_404(Category, pk=pk)
            category.delete()
            return Response(
                {"details": f"Category {pk} deleted successfully"},
                status=status.HTTP_204_NO_CONTENT,
            )

        Category.objects.all().delete()
        return Response(
            {"details": "All categories deleted successfully"},
            status=status.HTTP_204_NO_CONTENT,
        )