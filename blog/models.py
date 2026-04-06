from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.urls import reverse
from django.utils.text import slugify
from markdownx.models import MarkdownxField
from markdownx.utils import markdownify
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

from django.db.models.signals import post_save
from django.dispatch import receiver



@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    if hasattr(instance, 'profile'):
        instance.profile.save()

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name_plural = "Categories"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('category_posts', args=[self.slug])

class Post(models.Model):
    STATUS_CHOICES = (
        ('draft', 'Draft'),
        ('published', 'Published'),
    )
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=200, blank=True)
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='blog_posts')
    content = MarkdownxField()  # Markdown support
    featured_image = models.ImageField(upload_to='blog_images/', blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name='posts')
    tags = models.CharField(max_length=200, blank=True, help_text="Separate tags with commas")
    
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(default=timezone.now)
    
    # For engagement
    likes = models.ManyToManyField(User, related_name='liked_posts', blank=True)
    views = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-published_at']
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('post_detail', args=[self.slug])
    
    def total_likes(self):
        return self.likes.count()
    
    def formatted_content(self):
        return markdownify(self.content)
    
    def get_related_posts(self, limit=3):
        """Get related posts based on category and tags"""
        related = Post.objects.filter(status='published').exclude(id=self.id)
        
        # First try same category
        if self.category:
            related = related.filter(category=self.category)
        
        # If not enough, add posts with similar tags
        if related.count() < limit and self.tags:
            tags_list = [tag.strip() for tag in self.tags.split(',')[:2]]
            for tag in tags_list:
                tag_related = Post.objects.filter(
                    tags__icontains=tag, 
                    status='published'
                ).exclude(id=self.id)
                related = (related | tag_related).distinct()
        
        return related[:limit]

class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='comments')
    name = models.CharField(max_length=100)
    email = models.EmailField()
    body = models.TextField()
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f'Comment by {self.name} on {self.post.title}'
    
    def save(self, *args, **kwargs):
        # Send email notification on new comment
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new and self.post.author.email:
            self.send_notification_email()
    
    def send_notification_email(self):
        """Send email notification to post author"""
        subject = f'New comment on "{self.post.title}"'
        message = render_to_string('blog/email/comment_notification.html', {
            'comment': self,
            'post': self.post,
        })
        try:
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [self.post.author.email])
        except:
            pass  # Log error in production

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    website = models.URLField(blank=True)
    twitter_handle = models.CharField(max_length=100, blank=True)
    github_handle = models.CharField(max_length=100, blank=True)
    facebook_handle = models.CharField(max_length=100, blank=True)
    notification_email = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"