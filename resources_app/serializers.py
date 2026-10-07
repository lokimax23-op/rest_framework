from rest_framework import serializers

from .models import LearningResource


class LearningResourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningResource
        fields = ['id', 'title', 'category', 'description', 'author', 'created_at']
        read_only_fields = ['id', 'author', 'created_at']
