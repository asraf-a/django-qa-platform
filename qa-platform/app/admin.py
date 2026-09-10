from django.contrib import admin

from .models import Answer, Comment, Question, Tag, Vote


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'score', 'created_at')
    search_fields = ('title', 'description')
    list_filter = ('created_at', 'tags')
    filter_horizontal = ('tags',)


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'author', 'score', 'created_at')
    search_fields = ('content',)
    list_filter = ('created_at',)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'get_root_target', 'parent', 'score', 'created_at')
    search_fields = ('content',)
    list_filter = ('created_at',)


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ('user', 'content_type', 'object_id', 'value', 'created_at')
    list_filter = ('value', 'content_type', 'created_at')
