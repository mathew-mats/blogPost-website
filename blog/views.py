from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.text import slugify
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from markdownx.utils import markdownify

from .models import Post, Category, Comment, UserProfile
from .forms import CommentForm, PostForm, UserRegistrationForm, UserProfileForm
from .utils import get_client_ip
from django.utils import timezone


def categories_json(request):
    """API endpoint to get categories as JSON"""
    categories = Category.objects.all().values('id', 'name')
    return JsonResponse({'categories': list(categories)})


def register(request):
    """User registration view"""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'blog/register.html', {'form': form})


def login_view(request):
    """User login view"""
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, f'Welcome back {user.username}!')
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'blog/login.html', {'form': form})


def logout_view(request):
    """User logout view"""
    auth_logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('home')


def home(request):
    """Home page displaying all published posts"""
    posts = Post.objects.filter(status='published').order_by('-published_at')
    
    # Pagination
    paginator = Paginator(posts, 5)
    page = request.GET.get('page', 1)
    
    try:
        posts = paginator.page(page)
    except PageNotAnInteger:
        posts = paginator.page(1)
    except EmptyPage:
        posts = paginator.page(paginator.num_pages)
    
    # Get data for sidebar
    categories = Category.objects.annotate(post_count=Count('posts')).filter(post_count__gt=0)
    recent_posts = Post.objects.filter(status='published').order_by('-published_at')[:5]
    popular_posts = Post.objects.filter(status='published').order_by('-views')[:5]
    
    context = {
        'posts': posts,
        'title': 'Home',
        'categories': categories,
        'recent_posts': recent_posts,
        'popular_posts': popular_posts,
    }
    return render(request, 'blog/home.html', context)


def post_detail(request, slug):
    """Display single post details"""

    post = get_object_or_404(Post, slug=slug, status='published')
    
    # Update view count
    post.views += 1
    post.save()
    
    # Get related posts
    related_posts = post.get_related_posts()
    
    # Comments
    comments = post.comments.filter(active=True)
    
    if request.method == 'POST' and request.user.is_authenticated:
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.post = post
            comment.user = request.user
            comment.name = request.user.username
            comment.email = request.user.email
            comment.save()
            messages.success(request, 'Your comment has been added!')
            return redirect('post_detail', slug=post.slug)
    else:
        comment_form = CommentForm()
    
    # Get data for sidebar
    categories = Category.objects.annotate(post_count=Count('posts'))
    recent_posts = Post.objects.filter(status='published').order_by('-published_at')[:5]
    popular_posts = Post.objects.filter(status='published').order_by('-views')[:5]
    
    context = {
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
        'related_posts': related_posts,
        'title': post.title,
        'categories': categories,
        'recent_posts': recent_posts,
        'popular_posts': popular_posts,
        'total_likes': post.total_likes(),
        'user_liked': request.user in post.likes.all() if request.user.is_authenticated else False,
        'formatted_content': markdownify(post.content),
    }
    return render(request, 'blog/post_detail.html', context)





@login_required
def like_post(request, post_id):
    """Handle post likes"""
    post = get_object_or_404(Post, id=post_id)
    
    if request.user in post.likes.all():
        post.likes.remove(request.user)
        messages.info(request, 'You unliked this post')
    else:
        post.likes.add(request.user)
        messages.success(request, 'You liked this post!')
    
    # Redirect back to the post
    return redirect('post_detail', slug=post.slug)

@login_required
def create_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.status = 'published'  # Force published status
            post.published_at = timezone.now()  # Set current time
            
            # Auto-generate slug if not provided
            if not post.slug:
                post.slug = slugify(post.title)
            
            # Ensure unique slug
            original_slug = post.slug
            counter = 1
            while Post.objects.filter(slug=post.slug).exists():
                post.slug = f"{original_slug}-{counter}"
                counter += 1
            
            post.save()
            messages.success(request, f'Your post "{post.title}" has been created and published!')
            return redirect('post_detail', slug=post.slug)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PostForm()
    
    # Get data for sidebar
    categories = Category.objects.all()
    recent_posts = Post.objects.filter(status='published').order_by('-published_at')[:5]
    popular_posts = Post.objects.filter(status='published').order_by('-views')[:5]
    
    context = {
        'form': form,
        'categories': categories,
        'recent_posts': recent_posts,  # Add this
        'popular_posts': popular_posts,  # Add this
        'title': 'Create Post',
    }
    return render(request, 'blog/create_post.html', context)


@login_required
def profile(request, username=None):
    """Display user profile"""
    if username:
        profile_user = get_object_or_404(User, username=username)
    else:
        profile_user = request.user
    
    user_posts = Post.objects.filter(author=profile_user, status='published')
    
    # Ensure profile exists
    if not hasattr(profile_user, 'profile'):
        UserProfile.objects.create(user=profile_user)
    
    # Get data for sidebar
    categories = Category.objects.annotate(post_count=Count('posts'))
    recent_posts = Post.objects.filter(status='published').order_by('-published_at')[:5]
    popular_posts = Post.objects.filter(status='published').order_by('-views')[:5]
    
    context = {
        'profile_user': profile_user,
        'user_posts': user_posts,
        'total_posts': user_posts.count(),
        'total_likes_received': sum(post.total_likes() for post in user_posts),
        'categories': categories,  # Add this
        'recent_posts': recent_posts,  # Add this
        'popular_posts': popular_posts,  # Add this
    }
    return render(request, 'blog/profile.html', context)


@login_required
def edit_profile(request):
    """Edit user profile"""
    if not hasattr(request.user, 'profile'):
        UserProfile.objects.create(user=request.user)
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user.profile)
    
    # Get data for sidebar
    categories = Category.objects.annotate(post_count=Count('posts'))
    recent_posts = Post.objects.filter(status='published').order_by('-published_at')[:5]
    popular_posts = Post.objects.filter(status='published').order_by('-views')[:5]
    
    context = {
        'form': form,
        'categories': categories,
        'recent_posts': recent_posts,
        'popular_posts': popular_posts,
    }
    return render(request, 'blog/edit_profile.html', context)


def category_posts(request, slug):
    """Display posts in a specific category"""
    category = get_object_or_404(Category, slug=slug)
    posts = Post.objects.filter(category=category, status='published').order_by('-published_at')
    
    paginator = Paginator(posts, 10)
    page = request.GET.get('page', 1)
    posts = paginator.get_page(page)
    
    # Get data for sidebar
    categories = Category.objects.annotate(post_count=Count('posts'))
    recent_posts = Post.objects.filter(status='published').order_by('-published_at')[:5]
    popular_posts = Post.objects.filter(status='published').order_by('-views')[:5]
    
    context = {
        'category': category,
        'posts': posts,
        'title': f'Category: {category.name}',
        'categories': categories,
        'recent_posts': recent_posts,
        'popular_posts': popular_posts,
    }
    return render(request, 'blog/category_posts.html', context)


def search(request):
    """Search blog posts"""
    query = request.GET.get('q', '')
    posts = Post.objects.filter(status='published')
    
    if query:
        posts = posts.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(tags__icontains=query)
        ).distinct()
    
    # Get data for sidebar
    categories = Category.objects.annotate(post_count=Count('posts'))
    recent_posts = Post.objects.filter(status='published').order_by('-published_at')[:5]
    popular_posts = Post.objects.filter(status='published').order_by('-views')[:5]
    
    context = {
        'posts': posts,
        'query': query,
        'title': f'Search results for "{query}"',
        'categories': categories,
        'recent_posts': recent_posts,
        'popular_posts': popular_posts,
    }
    return render(request, 'blog/search.html', context)

