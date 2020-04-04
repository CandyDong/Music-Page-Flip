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

from .signals import flip_page_signal

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


import os
import cv2
import numpy as np
import pytesseract
from fuzzywuzzy import fuzz
import PIL
import socket

HOST = "127.0.0.1"
PORT = 65432

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
    new_profile = Profile.objects.create(user=new_user)
    new_profile.save()

    new_user = authenticate(username=form.cleaned_data['username'],
                            password=form.cleaned_data['password'])

    login(request, new_user)
    return redirect(reverse('homepage'))

def connect_rpi(request):
    context = {}
    available_rpis = RPI.objects.all().filter(in_use=False)
    print("available rpi: {}".format(available_rpis))
    if (len(available_rpis) > 0):
        rpi_to_use = available_rpis.first()
        print("rpi_to_use: {}".format(rpi_to_use))
        rpi_to_use.in_use = True
        request.user.profile.rpi = rpi_to_use
        request.user.profile.save()
        return redirect('select')

    context['message'] = "All rpis are in use now, please try again later."
    return render(request, 'pageFlipper/homepage.html', context)

##TODO !!!!!
def disconnect_rpi(request):
    context = {}
    available_rpi = RPI.objects.get(pk=1)
    available_rpi.in_use = '0'
    available_rpi.save()
    request.user.profile.rpiId = ''
    request.user.profile.save()
    return render(request, 'pageFlipper/homepage.html', context)


def select_score(request):
    def _send_title(title):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(title.encode('utf-8'))
            reply = s.recv(1024)
            if not reply != 1:
                print("ERROR!!!")
                return
            print("SUCCESS sending title to python script.")
    context = {}
    if request.POST:
        score_name = request.POST['selected_score']
        score_path = os.path.join("pageFlipper", settings.MEDIA_URL, \
                            score_name, score_name+"_1.png")
        _send_title(score_name)
        base_url = reverse('display')  
        query_string =  urlencode({"score_name": score_name, \
                                    "page": 1})  
        url = '{}?{}'.format(base_url, query_string) 
        return redirect(url)
    return redirect('select')


def select_page(request):
    context = {}
    context['scores'] = request.user.profile.score_set.all()
    context['form'] = ScoreForm()
    return render(request, 'pageFlipper/select.html', context)


def _readTitle(inputImg):
    image = cv2.imread(inputImg)
    copy = image.copy()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.threshold(gray, 0, 255,
        cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

    # find contours
    (contours, _) = cv2.findContours(~gray,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE) 

    for contour in contours:
        """
        draw a rectangle around those contours on main image
        """
        [x,y,w,h] = cv2.boundingRect(contour)
        cv2.rectangle(copy, (x,y), (x+w,y+h), (0, 255, 0), 1)
    # cv2.imwrite('contours.png', copy)

    # create blank image of same dimension of the original image
    mask = np.ones(copy.shape[:2], dtype="uint8") * 255 

    # Collecting y value of each contour
    (contours, _) = cv2.findContours(~gray,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE) 

    ys = []
    for c in contours:
        [x,y,w,h] = cv2.boundingRect(c)
        ys.append(y)
    ys.sort()

    # Get the y value of possible title positions, 
    # requires the black space above music score to be narrow
    # threshold 20px difference between starting position of all words of a title
    accepted_ys = []
    for i in range(len(ys)):
        if i == 0:
            accepted_ys.append(ys[i])
        else:
            if(ys[i] - ys[i-1] <= 20):
                accepted_ys.append(ys[i])
            else:
                break
    
    for c in contours:
        [x,y,w,h] = cv2.boundingRect(c)
        if y in accepted_ys:
            cv2.drawContours(mask, [c], -1, 0, -1)

    filename = "{}.png".format(os.getpid())
    cv2.imwrite(filename, mask)
    # load the image as a PIL/Pillow image, apply OCR, and then delete
    # the temporary file
    text = pytesseract.image_to_string(PIL.Image.open(filename))
    os.remove(filename)
    # show the output images
    # cv2.imwrite("Image.png", image)
    # cv2.imwrite("Output.png", gray)
    return text


def _getDBTitles():
    L = []
    for name in os.listdir(settings.MEDIA_ROOT):
        if os.path.isdir(os.path.join(settings.MEDIA_ROOT, name)):
            L.append(name)
    return L


def _matchTitle(inputTitle, L):
    maxRatio = 0
    scoreTitle = None
    for title in L:
        ratio = fuzz.partial_ratio(inputTitle, title)
        if(ratio > maxRatio):
            maxRatio = ratio
            scoreTitle = title
    return scoreTitle


def _getTitle():
    mediaFolder = "images"
    for filename in os.listdir(settings.MEDIA_ROOT):
        if (filename.endswith('.png') and not 'default' in filename):
            img_path = os.path.join(settings.MEDIA_ROOT, filename)
    img_title = _readTitle(img_path)
    print('Recognized title: ' + img_title)

    db_titles = _getDBTitles()
    print('Database titles: ', db_titles)

    score_title = _matchTitle(img_title, db_titles)
    print('Most closely resembled title in database: ' + score_title)

    for filename in os.listdir(settings.MEDIA_ROOT):
        if (filename.endswith('.png') and not 'default' in filename):
            os.remove(os.path.join(settings.MEDIA_ROOT, filename))

    return score_title


def add_score(request):
    def _send_title(title):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((HOST, PORT))
            s.sendall(title.encode('utf-8'))
            reply = s.recv(1024)
            if not reply != 1:
                print("ERROR!!!")
                return
            print("SUCCESS sending title to python script.")

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

    _send_title(title)

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


def display_page(request):
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
    print("title: {}".format(title))
    flip_to = request.POST.get("flip_to")
    score = Score.objects.get(scoreName=title)
    new_path = os.path.join(settings.MEDIA_URL, \
                            title, title+"_{}.png".format(flip_to))
    with open(os.path.join("pageFlipper", new_path), encoding = "ISO-8859-1") as f:
        wrapped_file = File(f)
        score.pic = wrapped_file
        score.path = new_path
        score.save()

    print("new_path: {}".format(new_path))

    base_url = reverse('display')  
    query_string =  urlencode({"score_name": score.scoreName, \
                                "page": int(flip_to)})
    url = '{}?{}'.format(base_url, query_string) 
    return redirect(url)


def update_page(request):
    if request.method == "GET" and request.is_ajax():
        score_name = request.GET["score_name"]
        score = Score.objects.get(scoreName=score_name)
        return JsonResponse({"score_name": score.scoreName, "path": score.path})
    else:
        return HttpResponseBadRequest(u"Invalid Request") 


def homepage(request):
    context = {}
    return render(request, 'pageFlipper/homepage.html', context)

def profile(request):
    context = {}
    context['scores'] = request.user.profile.scores.all()
    return render(request, 'pageFlipper/profile.html', context)
