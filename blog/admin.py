from django.contrib import admin
from .models import Category, Post, Comment

# Register your models here.

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'category', 'status', 'created_at', 'total_likes']
    list_filter = ['status', 'created_at', 'category']
    search_fields = ['title', 'content']
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ['author']
    date_hierarchy = 'published_at'
    actions = ['make_published']
    
    def make_published(self, request, queryset):
        queryset.update(status='published')
    make_published.short_description = "Mark selected posts as published"

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['name', 'post', 'created_at', 'active']
    list_filter = ['active', 'created_at']
    search_fields = ['name', 'body']
    actions = ['approve_comments']
    
    def approve_comments(self, request, queryset):
        queryset.update(active=True)
    approve_comments.short_description = "Approve selected comments"