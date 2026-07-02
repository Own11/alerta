from rest_framework import serializers
from .models import Project

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            'id', 'user', 'name', 'description', 'slug', 
            'status_page_enabled', 'status_page_title', 'status_page_logo'
        ]
        read_only_fields = ['id', 'user', 'slug']
