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
from pageFlipper.models import Profile, Score, RPI, FlipSession

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
import pickle

# state macros
SESSION_START = 1
SESSION_END = 2

DEBUG = True

def login_action(request):
    context = {}

    if request.user.is_authenticated:
        try:
            user_rpi = RPI.objects.get(user_profile=request.user.profile)
        except RPI.DoesNotExist:
            return redirect(reverse('homepage'))
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
    flipSession = FlipSession.objects.create(user_profile=new_profile)
    flipSession.save()

    new_user = authenticate(username=form.cleaned_data['username'],
                            password=form.cleaned_data['password'])

    login(request, new_user)

    return redirect(reverse('homepage'))


@login_required
def connect_rpi(request):
    if not request.method == "POST":
        return HttpResponseBadRequest(u"Invalid Request") 

    available_rpis = RPI.objects.filter(in_use=False)
    if (len(available_rpis) == 0):
        return redirect(Reverse('homepage'))
    rpi_to_use = available_rpis.first()
    rpi_to_use.in_use = True
    rpi_to_use.user_profile = request.user.profile
    rpi_to_use.save()

    # pk = request.POST["rpi_choices"]
    # context = {}
    # rpi_to_use = RPI.objects.all().get(pk=pk)
    # rpi_to_use.in_use = True
    # rpi_to_use.user_profile = request.user.profile
    # rpi_to_use.save()

    return redirect('select')


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

    flipSession = FlipSession.objects.get(user_profile=request.user.profile)
    flipSession.state = SESSION_END
    flipSession.score = None
    flipSession.save()
    if DEBUG: print("session: {}".format(flipSession))

    return redirect(reverse('homepage'))


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
    print("scores: {}".format(context['scores']))
    context['form'] = ScoreForm()

    flipSession = FlipSession.objects.get(user_profile=request.user.profile)
    flipSession.state = None
    flipSession.save()
    if DEBUG: print("session: {}".format(flipSession))

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

    old_scores = Score.objects.all().filter(user_profiles=request.user.profile, scoreName=title)
    if (len(old_scores) > 0):
        context['form'] = form
        context['scores'] = request.user.profile.score_set.all()
        context["message"] = "Score with same name has already been uploaded. \
                            Please select it from the dropdown box."
        return render(request, 'pageFlipper/select.html', context)

    try:
        same_score = Score.objects.get(scoreName=title)
        same_score.user_profiles.add(request.user.profile)
        request.user.profile.score_set.add(same_score)
        same_score.save()
        new_score.delete()
        base_url = reverse('display')  
        query_string =  urlencode({"score_name": same_score.scoreName, \
                                    "page": 1})  
        url = '{}?{}'.format(base_url, query_string) 
        return redirect(url)
    except Score.DoesNotExist:
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

    flipSession = FlipSession.objects.get(user_profile=request.user.profile)
    flipSession.state = SESSION_START
    flipSession.score_name = score_name
    flipSession.save()
    if DEBUG: print("session: {}".format(flipSession))

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

@csrf_exempt
def get_state(request):
    if request.method != "POST":
        return HttpResponseBadRequest(u"Invalid Request")
    # userid = request.POST.get("userid")
    # user = User.objects.get(pk=userid)
    # user_profile = user.profile
    try:
        rpi_in_use = RPI.objects.get(in_use=True)
    except DoesNotExist:
        return JsonResponse({"state":None, \
                        "score_name": None})
    user_profile = rpi_in_use.user_profile

    try:
        flipSession = FlipSession.objects.get(user_profile=user_profile)
    except FlipSession.DoesNotExist:
        return JsonResponse({"state":None, \
                        "score_name": None})
    return JsonResponse({"state":flipSession.state, \
                        "score_name": flipSession.score_name})

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
    try:
        user_rpi = RPI.objects.get(user_profile=request.user.profile)
        return redirect(reverse('select'))
    except RPI.DoesNotExist:
        available_rpis = RPI.objects.filter(in_use=False)
        # unavailable_rpis = RPI.objects.filter(in_use=True)
        if (len(available_rpis) == 0):
            context["message"] = "No available PageFlipper for now. Please check back later."
        # context["unavailable_rpis"] = unavailable_rpis
        # context['form'] = RPIForm()

    flipSession = FlipSession.objects.get(user_profile=request.user.profile)
    flipSession.state = None
    flipSession.save()
    if DEBUG: print("session: {}".format(flipSession))

    return render(request, 'pageFlipper/homepage.html', context)

@login_required
def profile(request):
    context = {}
    context['scores'] = request.user.profile.score_set.all()
    return render(request, 'pageFlipper/profile.html', context)


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
    cv2.imwrite(os.path.join(settings.MEDIA_ROOT, filename), mask)
    # load the image as a PIL/Pillow image, apply OCR, and then delete
    # the temporary file
    text = pytesseract.image_to_string(PIL.Image.open(os.path.join(settings.MEDIA_ROOT, filename)))
    os.remove(os.path.join(settings.MEDIA_ROOT, filename))
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


##########Title Recognition Utils##################

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
    cv2.imwrite(os.path.join(settings.MEDIA_ROOT, filename), mask)
    # load the image as a PIL/Pillow image, apply OCR, and then delete
    # the temporary file
    text = pytesseract.image_to_string(PIL.Image.open(os.path.join(settings.MEDIA_ROOT, filename)))
    os.remove(os.path.join(settings.MEDIA_ROOT, filename))
    print("temporary file at {} removed.".format(os.path.join(settings.MEDIA_ROOT, filename)))
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


        








