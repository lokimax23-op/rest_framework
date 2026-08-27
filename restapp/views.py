from django.shortcuts import render
from restapp.serializers import CategorySerializer, MenuSerializer
from restapp.models import Menu , Category
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
# Create your views here.

@api_view(['POST','GET'])
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
