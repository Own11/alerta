import uuid
from django.db import models
from django.conf import settings
from django.utils.text import slugify

class Project(models.Model):
    """
    Модель проекта для группировки мониторов.
    Каждый проект может иметь публичную статус-страницу.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='projects')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    
    # Статус страница
    status_page_enabled = models.BooleanField(default=False)
    status_page_title = models.CharField(max_length=255, blank=True, null=True)
    status_page_logo = models.URLField(blank=True, null=True)

    class Meta:
        db_table = 'projects_project'

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or "project"
            slug = base_slug
            counter = 1
            while Project.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
