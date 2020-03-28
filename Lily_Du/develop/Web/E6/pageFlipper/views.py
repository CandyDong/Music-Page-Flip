from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404

from django.shortcuts import render, redirect
from django.urls import reverse

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout

from django.utils import timezone

from pageFlipper.forms import LoginForm, RegistrationForm 
from pageFlipper.models import Profile, Score, RPI

from django.db import transaction
from django.utils import timezone

def login_action(request):
    context = {}

    # Just display the registration form if this is a GET request.
    if request.method == 'GET':
        context['form'] = LoginForm()
        return render(request, 'pageFlipper/login.html', context)

    # Creates a bound form from the request POST parameters and makes the 
    # form available in the request context dictionary.
    form = LoginForm(request.POST)
    context['form'] = form

    # Validates the form.
    if not form.is_valid():
        return render(request, 'pageFlipper/login.html', context)

    new_user = authenticate(username=form.cleaned_data['username'],
                            password=form.cleaned_data['password'])

    login(request, new_user)
    return redirect(reverse('homepage'))

def logout_action(request):
    logout(request)
    return redirect(reverse('login'))

def register_action(request):
    context = {}

    # Just display the registration form if this is a GET request.
    if request.method == 'GET':
        context['form'] = RegistrationForm()
        return render(request, 'pageFlipper/register.html', context)

    # Creates a bound form from the request POST parameters and makes the 
    # form available in the request context dictionary.
    form = RegistrationForm(request.POST)
    context['form'] = form

    # Validates the form.
    if not form.is_valid():
        return render(request, 'pageFlipper/register.html', context)

    # At this point, the form data is valid.  Register and login the user.
    new_user = User.objects.create_user(username=form.cleaned_data['username'], 
                                        password=form.cleaned_data['password'])
    new_user.save()
    Profile.objects.create(user=new_user)

    new_user = authenticate(username=form.cleaned_data['username'],
                            password=form.cleaned_data['password'])

    login(request, new_user)
    return redirect(reverse('homepage'))

def connect_rpi(request):
    context = {}
    available_rpi = RPI.objects.get(pk=1)
    if(available_rpi.in_use == '0'):
        available_rpi.in_use = '1'
        available_rpi.save()
        request.user.profile.rpiId = '1'
        request.user.profile.save()
        return redirect('select')

    context['message'] = "All rpis in use, please try again later."
    return render(request, 'pageFlipper/homepage.html', context)

def disconnect_rpi(request):
    context = {}
    available_rpi = RPI.objects.get(pk=1)
    available_rpi.in_use = '0'
    available_rpi.save()
    request.user.profile.rpiId = ''
    request.user.profile.save()
    return render(request, 'pageFlipper/homepage.html', context)

def select_score(request):
    context = {}
    if request.POST:
        score = request.POST['selected_score']
        context['scoreName'] = score
        return render(request, 'pageFlipper/display.html', context)
    return redirect('display')

def selectpage(request):
    context = {}
    context['scores'] = request.user.profile.scores.all()
    return render(request, 'pageFlipper/select.html', context)

def displaypage(request):
    context = {}
    return render(request, 'pageFlipper/display.html', context)

def homepage(request):
    context = {}
    return render(request, 'pageFlipper/homepage.html', context)

def profile(request):
    context = {}
    context['scores'] = request.user.profile.scores.all()
    return render(request, 'pageFlipper/profile.html', context)