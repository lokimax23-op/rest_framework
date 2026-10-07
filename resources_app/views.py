from rest_framework import generics
from rest_framework.permissions import IsAuthenticatedOrReadOnly

from .models import LearningResource
from .permissions import IsAuthorOrReadOnly
from .serializers import LearningResourceSerializer


class LearningResourceListCreateView(generics.ListCreateAPIView):
    queryset = LearningResource.objects.select_related('author').all()
    serializer_class = LearningResourceSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class LearningResourceDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = LearningResource.objects.select_related('author').all()
    serializer_class = LearningResourceSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
