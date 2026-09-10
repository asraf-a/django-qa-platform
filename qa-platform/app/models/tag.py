from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.functions import Lower
from django.utils.text import slugify


class Tag(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(max_length=50, unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                Lower('name'),
                name='unique_tag_name_case_insensitive'
            )
        ]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()
        if self.name:
            stripped_name = self.name.strip()
            if Tag.objects.filter(name__iexact=stripped_name).exclude(pk=self.pk).exists():
                raise ValidationError({'name': 'A tag with this name already exists.'})

    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            base_slug = slugify(self.name.lower())
            if not base_slug:
                base_slug = 'tag'
            slug = base_slug
            counter = 1
            while Tag.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)
