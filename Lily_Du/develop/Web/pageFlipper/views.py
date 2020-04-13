from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt

from django.shortcuts import render, redirect
from django.urls import reverse
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout

from django.utils import timezone

from pageFlipper.forms import LoginForm, RegistrationForm, ScoreForm
from pageFlipper.models import Profile, Score, RPI

from django.db.models.signals import post_save
from django.dispatch import receiver

from django.conf import settings
from django.core.files import File

from django.db import transaction
from django.utils import timezone

import json
from django.http import JsonResponse

from .utils import *

import os
import cv2
import numpy as np
import pytesseract
from fuzzywuzzy import fuzz
import PIL
import socket

TITLE = 0x01
END_SESSION = 0x02
REPLY = 0x03

HOST = "127.0.0.1"
PORT = 65432
# S = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# S.connect((HOST, PORT))


def login_action(request):
    context = {}

    if request.user.is_authenticated:
        try:
            user_rpi = RPI.objects.get(user_profile=request.user.profile)
        except RPI.DoesNotExist:
            return redirect(reverse('connect-rpi'))
        return redirect(reverse('select'))

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

    # if user is already linked to a rpi, jump to the session page
    user_profile = request.user.profile
    try:
        user_rpi = RPI.objects.get(user_profile=user_profile)
    except RPI.DoesNotExist:
        return redirect(reverse('homepage'))

    return redirect(reverse('select'))


@login_required
def logout_action(request):
    user_profile = request.user.profile
    try:
        user_rpi = RPI.objects.get(user_profile=request.user.profile)
        user_rpi.user_profile = None
        user_rpi.in_use = False
        user_rpi.save()
        # _send(END_SESSION, None)
    except RPI.DoesNotExist:
        pass
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
    new_profile = Profile.objects.create(user=new_user)
    new_profile.save()

    new_user = authenticate(username=form.cleaned_data['username'],
                            password=form.cleaned_data['password'])

    login(request, new_user)

    return redirect(reverse('homepage'))


@login_required
def connect_rpi(request):
    try:
        user_rpi = RPI.objects.get(user_profile=request.user.profile)
        return redirect(reverse('select'))
    except RPI.DoesNotExist:
        context = {}
        available_rpis = RPI.objects.all().filter(in_use=False)
        print("available rpi: {}".format(available_rpis))
        if (len(available_rpis) > 0):
            rpi_to_use = available_rpis.first()
            print("rpi_to_use: {}".format(rpi_to_use))
            rpi_to_use.in_use = True
            rpi_to_use.user_profile = request.user.profile
            rpi_to_use.save()
            return redirect('select')
        context['message'] = "All rpis are in use now, please try again later."
    return render(request, 'pageFlipper/homepage.html', context)


@login_required
def disconnect_rpi(request, score_name):
    user_profile = request.user.profile
    rpi_in_use = RPI.objects.get(user_profile=user_profile)
    rpi_in_use.in_use = False
    rpi_in_use.user_profile = None
    rpi_in_use.save()

    score = Score.objects.get(scoreName=score_name)
    score.pic.delete()
    with open(os.path.join("pageFlipper", settings.MEDIA_URL, \
                            score_name, score_name+"_1.png"), \
                            encoding = "ISO-8859-1") as f:
        wrapped_file = File(f)
        score.pic = wrapped_file
        score.path = os.path.join(settings.MEDIA_URL, \
                                    score_name, score_name+"_1.png")
        score.save()

    # _send(END_SESSION, None)
    return render(request, 'pageFlipper/homepage.html')


@login_required
def select_score(request):
    if request.method != "POST":
        return HttpResponseBadRequest(u"Invalid Request") 

    context = {}

    score_name = request.POST['selected_score']
    score_path = os.path.join(settings.MEDIA_URL, \
                        score_name, score_name+"_1.png")
    score = Score.objects.get(scoreName=score_name)
    score.path = score_path
    score.save()

    # _send(TITLE, score_name)
    base_url = reverse('display')  
    query_string =  urlencode({"score_name": score_name, \
                                "page": 1})  
    url = '{}?{}'.format(base_url, query_string) 
    return redirect(url)


@login_required
def select_page(request):
    try:
        user_rpi = RPI.objects.get(user_profile=request.user.profile)
    except RPI.DoesNotExist:
        return redirect(reverse('homepage'))
        
    context = {}
    context['scores'] = request.user.profile.score_set.all()
    context['form'] = ScoreForm()
    return render(request, 'pageFlipper/select.html', context)

@login_required
def add_score(request):
    context = {}
    new_score = Score(scoreName="temp")
    form = ScoreForm(request.POST, request.FILES, instance=new_score)
    if not form.is_valid():
        context['form'] = form
        context['scores'] = request.user.profile.score_set.all()
        return render(request, 'pageFlipper/select.html', context)
    
    pic = form.cleaned_data['pic']
    print('Uploaded sheet music: {} (type={})'.format(pic, type(pic)))

    new_score.content_type = form.cleaned_data['pic'].content_type
    form.save()

    title = _getTitle()
    print("recognized sheet music title is: {}".format(title))

    old_scores = Score.objects.all().filter(scoreName=title)
    if len(old_scores) > 0:
        context['form'] = form
        context['scores'] = request.user.profile.score_set.all()
        context["message"] = "Score with same name has already been uploaded. \
                            Please select it from the dropdown box."
        return render(request, 'pageFlipper/select.html', context)

    # _send(TITLE, title)

    new_score.scoreName = title
    new_score.pic.delete()
    with open(os.path.join("pageFlipper", settings.MEDIA_URL, \
                            title, title+"_1.png"), \
                            encoding = "ISO-8859-1") as f:
        wrapped_file = File(f)
        new_score.pic = wrapped_file
        new_score.path = os.path.join(settings.MEDIA_URL, \
                                    title, title+"_1.png")
        new_score.save()
    
    request.user.profile.score_set.add(new_score)
    base_url = reverse('display')  
    query_string =  urlencode({"score_name": new_score.scoreName, \
                                "page": 1})  
    url = '{}?{}'.format(base_url, query_string) 
    return redirect(url)

@login_required
def display_page(request):
    try:
        user_rpi = RPI.objects.get(user_profile=request.user.profile)
    except RPI.DoesNotExist:
        return redirect(reverse('homepage'))

    score_name = request.GET.get("score_name")
    page = request.GET.get("page")
    score = Score.objects.get(scoreName=score_name)
    return render(request, 'pageFlipper/display.html', \
                        {"score_name": score.scoreName, "score_path": score.path})


@csrf_exempt
def flip_page(request):
    if request.method != "POST":
        return HttpResponseBadRequest(u"Invalid Request") 
    # print(json.loads(request.body.decode('utf-8')))
    title = request.POST.get("score_name")
    flip_to = request.POST.get("flip_to")
    score = Score.objects.get(scoreName=title)
    new_path = os.path.join(settings.MEDIA_URL, \
                            title, title+"_{}.png".format(flip_to))
    with open(os.path.join("pageFlipper", new_path), encoding = "ISO-8859-1") as f:
        wrapped_file = File(f)
        score.pic = wrapped_file
        score.path = new_path
        score.save()

    base_url = reverse('display')  
    query_string =  urlencode({"score_name": score.scoreName, \
                                "page": int(flip_to)})
    url = '{}?{}'.format(base_url, query_string) 
    return redirect(url)

@login_required
def button_flip(request):
    if request.method != "POST":
        return HttpResponseBadRequest(u"Invalid Request") 

    score_name = request.POST.get("score_name")
    direction = request.POST.get("direction")

    score = Score.objects.get(scoreName=score_name)
    cur_path = score.path
    hypen = -cur_path[::-1].find("_")
    dot = -cur_path[::-1].find(".")
    page_num = int(cur_path[hypen:dot-1])

    if direction == "f":
        offset = 1
    elif direction == "b":
        offset = -1
    else:
        return HttpResponseBadRequest(u"Invalid Request") 

    new_path = os.path.join(settings.MEDIA_URL, \
                                score_name, score_name+"_{}.png".format(page_num+offset))

    if os.path.exists(os.path.join("pageFlipper", new_path)):
        with open(os.path.join("pageFlipper", new_path), encoding = "ISO-8859-1") as f:
            wrapped_file = File(f)
            score.pic = wrapped_file
            score.path = new_path
            score.save()

    return JsonResponse({"score_name": score.scoreName, "path": score.path})
    
@login_required
def update_page(request):
    if request.method == "GET" and request.is_ajax():
        score_name = request.GET["score_name"]
        score = Score.objects.get(scoreName=score_name)
        return JsonResponse({"score_name": score.scoreName, "path": score.path})
    else:
        return HttpResponseBadRequest(u"Invalid Request") 

@login_required
def homepage(request):
    context = {}
    return render(request, 'pageFlipper/homepage.html', context)

@login_required
def profile(request):
    context = {}
    context['scores'] = request.user.profile.scores.all()
    return render(request, 'pageFlipper/profile.html', context)

###########TCP communication with the tracker program################
def _send(content_id, content):
    global S   
    msg = bytearray()
    msg.append(content_id)
    if content_id != END_SESSION:
        msg += content.encode('utf-8')
    S.sendall(msg)
    # while True:
    #     reply = S.recv(1024)
    #     if reply[0] == REPLY:
    #         if reply[1] == 1:
    #             print("SUCCESS")
    #         else:
    #             print("ERROR")
    #         return

        








