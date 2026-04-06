from django.contrib.syndication.views import Feed
from django.urls import reverse
from django.utils.feedgenerator import Rss201rev2Feed
from .models import Post

class LatestPostsFeed(Feed):
    title = "My Blog - Latest Posts"
    link = "http://127.0.0.1:8000/"  # Change this to your actual URL
    description = "Latest blog posts from My Blog"
    feed_url = "http://127.0.0.1:8000/feed/"  # Add this
    
    def items(self):
        return Post.objects.filter(status='published').order_by('-published_at')[:10]
    
    def item_title(self, item):
        return item.title
    
    def item_description(self, item):
        # Return a summary or truncated content
        if hasattr(item, 'summary') and item.summary:
            return item.summary[:200]
        # Strip HTML tags for RSS
        from django.utils.html import strip_tags
        return strip_tags(item.content)[:200]
    
    def item_pubdate(self, item):
        return item.published_at
    
    def item_link(self, item):
        # Use the full URL
        return f"http://127.0.0.1:8000{reverse('post_detail', args=[item.slug])}"
    
    def item_author_name(self, item):
        return item.author.username
    
    def item_categories(self, item):
        if item.category:
            return [item.category.name]
        return []