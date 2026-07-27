from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView
from usuarios import views as usuarios_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('core_api.urls')),
    path('login/', usuarios_views.LoginPersonalizadoView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('procesos/', include('procesos.urls')),
    path('', RedirectView.as_view(pattern_name='procesos:dashboard', permanent=False)),
    path('usuarios/', include('usuarios.urls')),
    path('catalogos/', include('catalogos.urls')),
]