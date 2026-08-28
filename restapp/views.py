from django.shortcuts import render
from restapp.serializers import CategorySerializer, MenuSerializer
from restapp.models import Menu, Category
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView  # Added missing import

# Function-based view
@api_view(['POST', 'GET'])
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

# Class-based view moved outside of the function above
class CategoryListView(APIView):
    def post(self, request):
        serializer = CategorySerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            # Combined message and data into a single dictionary payload
            return Response({
                "details": "Category created successfully",
                "data": serializer.data
            }, status=status.HTTP_201_CREATED)
        
    def get(self, request):
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)   
