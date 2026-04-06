from django.urls import path
from . import views
from .feeds import LatestPostsFeed

urlpatterns = [
    path('', views.home, name='home'),
    path('post/<slug:slug>/', views.post_detail, name='post_detail'),
    path('category/<slug:slug>/', views.category_posts, name='category_posts'),
    path('search/', views.search, name='search'),
    path('like/<int:post_id>/', views.like_post, name='like_post'),
    path('create/', views.create_post, name='create_post'),
    path('register/', views.register, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile, name='profile'),  # Current user profile
    path('profile/edit/', views.edit_profile, name='edit_profile'),  # Edit profile - MUST come before username pattern
    path('profile/<str:username>/', views.profile, name='profile_with_username'),  # Specific user profile - put this LAST
    path('feed/', LatestPostsFeed(), name='rss_feed'),
    path('categories-json/', views.categories_json, name='categories_json'),
]