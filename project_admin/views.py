import dateutil.parser
import requests
from django.db.models import Q
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView, ListView, TemplateView
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from .forms import TokenForm
from .models import Project, ProjectMember


class HomeView(ListView):
    template_name = "project_admin/home.html"
    context_object_name = 'project'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page'] = 'home'
        return context

    def get_queryset(self):
        try:
            return Project.objects.get(user=self.request.user)
        except Project.DoesNotExist:
            return redirect('login')


class LoginView(FormView):
    template_name = 'project_admin/login.html'
    form_class = TokenForm
    success_url = reverse_lazy('home')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page'] = 'login'
        return context

    def form_valid(self, form):
        token = form.cleaned_data['token']
        req_url = 'https://www.openhumans.org/api/' \
                  'direct-sharing/project/?access_token={}'.format(token)
        project_info = requests.get(req_url).json()
        try:
            user = User.objects.get_or_create(
                username=project_info['id_label']
            )[0]
            project_info['user'] = user
            project_info['token'] = token
            Project.objects.update_or_create(id=project_info['id'],
                                             defaults=project_info)
            login(self.request, user,
                  backend='django.contrib.auth.backends.ModelBackend')
            return redirect('home')
        except Exception as e:
            # Handle expired master tokens, or serve error message
            if 'detail' in project_info:
                messages.error(self.request, project_info['detail'] +
                               ' Check your token in the'
                               ' project management interface.', 'danger')
            else:
                messages.error(self.request, e, 'danger')
            return redirect('login')


class MembersView(TemplateView):
    template_name = 'project_admin/members.html'

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        project = Project.objects.get(user=self.request.user)
        token = project.token
        req_url = 'https://www.openhumans.org/api/direct-sharing' \
                  '/project/members/?access_token={}'.format(token)
        member_info = requests.get(req_url).json()
        try:
            members = member_info['results']
            project.projectmember_set.filter(
                ~Q(id__in=map(lambda x: int(x['project_member_id']), members))
            ).delete()
            for member in members:
                [m, _] = project.projectmember_set.get_or_create(id=int(member['project_member_id']),
                                                                 username=member.get('username'),
                                                                 date_joined=dateutil.parser.parse(member['created']))
                for file in member['data']:
                    project.file_set.update_or_create(id=file['id'],
                                                      basename=file['basename'],
                                                      created=dateutil.parser.parse(file['created']),
                                                      source=file['source'],
                                                      member=m,
                                                      defaults={
                                                          'download_url': file['download_url'],
                                                      })
            context.update({'page': 'members',
                            'members': project.projectmember_set.all(),
                            'groups': project.projectgroup_set.all()})
            return self.render_to_response(context)
        except Exception as e:
            if 'detail' in member_info:
                messages.error(self.request, member_info['detail'] +
                               ' Check your token in the'
                               ' project management interface.', 'danger')
            else:
                messages.error(self.request, e, 'danger')
            return redirect('login')


class LogoutView(TemplateView):

    def get(self, request, *args, **kwargs):
        logout(self.request)
        messages.info(self.request, 'You have been logged out!')
        return redirect('login')


def create_group(request):
    project = Project.objects.get(user=request.user)
    group = project.projectgroup_set.create(
        name=request.POST.get('new_group_name'),
        description=request.POST.get('new_group_description')
    )
    through_model = ProjectMember.groups.through
    through_model.objects.bulk_create([
        through_model(projectgroup=group, projectmember=member)
        for member in project.projectmember_set.filter(
            id__in=request.POST.getlist('selected_members')
        )
    ])
    return redirect('members')


def update_group(request, group_pk):
    project = Project.objects.get(user=request.user)
    group = project.projectgroup_set.get(pk=group_pk)
    group.name = request.POST.get('group_{}_name'.format(group_pk))
    group.description = request.POST.get('group_{}_description'
                                         .format(group_pk))
    group.save()
    return redirect('members')


def delete_group(request, group_pk):
    project = Project.objects.get(user=request.user)
    project.projectgroup_set.get(pk=group_pk).delete()
    return redirect('members')


def add_members(request):
    project = Project.objects.get(user=request.user)
    group = project.projectgroup_set.get(pk=request.POST.get('group_pk'))
    through_model = ProjectMember.groups.through
    through_model.objects.bulk_create([
        through_model(projectgroup=group, projectmember=member)
        for member in project.projectmember_set.filter(
            id__in=request.POST.getlist('selected_members')
        )
    ])
    return redirect('members')


def remove_member(request, group_id, member_id):
    project = Project.objects.get(user=request.user)
    group = project.projectgroup_set.get(pk=group_id)
    member = project.projectmember_set.get(id=member_id)
    through_model = ProjectMember.groups.through
    through_model.objects.filter(
        projectgroup=group, projectmember=member
    ).delete()
    return redirect('members')
