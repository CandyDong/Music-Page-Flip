from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.login_action, name='home'),
    path('login', views.login_action, name='login'),
    path('logout', views.logout_action, name='logout'),
    path('register', views.register_action, name='register'),
    path('homepage', views.homepage, name='homepage'),
    path('profile', views.profile, name='profile'),
    path('connect-rpi', views.connect_rpi, name='connect-rpi'),
    path('disconnect-rpi', views.disconnect_rpi, name='disconnect-rpi'),
    path('select', views.select_page, name='select'),
    path('select-score', views.select_score, name='select-score'),
    path('display', views.display_page, name='display'),
    path('add-score', views.add_score, name='add-score'),
    path('flip-page', views.flip_page, name='flip-page'),
    path('update-page', views.update_page),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
