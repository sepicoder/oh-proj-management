from django.urls import path
from django.contrib import admin
from django.contrib.auth.decorators import login_required

from project_admin.views import HomeView, MembersView, LoginView, LogoutView, \
    create_group, update_group, delete_group, add_members, remove_member

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', login_required(HomeView.as_view(), login_url='login/'),
         name='home'),
    path('members/', MembersView.as_view(), name='members'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('create_group/', create_group, name='create_group'),
    path('update_group/<int:group_pk>', update_group, name='update_group'),
    path('delete_group/<int:group_pk>/', delete_group, name='delete_group'),
    path('add_members/', add_members, name='add_members'),
    path('remove_member/<int:group_id>/<int:member_id>/', remove_member,
         name='remove_member')
]
