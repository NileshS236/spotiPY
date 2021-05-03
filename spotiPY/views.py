from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import login, authenticate, logout
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.utils.safestring import mark_safe

from .forms import AccountRegistrationForm, AccountAuthenticationForm
from .models import Account

import spotipy
import base64
import datetime
import requests
import pytz
import json
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
from urllib.parse import urlencode


CLIENT_ID = settings.SPOTIFY_CLIENT_ID
CLIENT_SECRET = settings.SPOTIFY_CLIENT_SECRET
REDIRECT_URI = settings.SPOTIFY_REDIRECT_URI
utc = pytz.UTC

scopes = "user-read-currently-playing,user-read-recently-played,user-read-playback-state,user-top-read,user-modify-playback-state"

spotify = spotipy.Spotify(
    auth_manager=SpotifyClientCredentials(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )
)


# Create your views here.


@login_required(login_url="spotiPY:login")
def home_view(request):
    context = {}
    user = request.user
    now = timezone.now()
    if user.is_authenticated:
        account = Account.objects.filter(email=user.email)[0]
        if not account.expiration or account.expiration < now:
            try:
                spotify_access_token, expiration = get_access_token()
                account.expiration = expiration
                account.spotify_access_token = spotify_access_token
                account.save()
                context["user"] = account
            except Exception as e:
                context["token_authentication_failed"] = e
        elif account.spotify_access_token == None:
            spotify_access_token, expiration = get_access_token()
            account.expiration = expiration
            account.spotify_access_token = spotify_access_token
            account.save()
            context["user"] = account
    return render(request, "home.html", context)


def signup_view(request, *args, **kwargs):
    user = request.user
    if user.is_authenticated:
        return redirect("spotiPY:home")
    context = {}
    spotify_access_token = ""
    form = AccountRegistrationForm()
    if request.POST:
        form = AccountRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            email = form.cleaned_data.get("email").lower()
            raw_password = form.cleaned_data.get("password1")
            account = authenticate(email=email, password=raw_password)
            return redirect("spotiPY:home")
    context["signup_form"] = form
    return render(request, "spotiPY/signup.html", context)


def login_view(request, *args, **kwargs):
    user = request.user
    if user.is_authenticated:
        return redirect("spotiPY:home")
    context = {}
    spotify_access_token = ""
    form = AccountAuthenticationForm()
    if request.POST:
        form = AccountAuthenticationForm(request.POST)
        if form.is_valid():
            email = request.POST["email"]
            password = request.POST["password"]
            user = authenticate(email=email, password=password)
            if user:
                login(request, user)
                return redirect("spotiPY:home")
    context["login_form"] = form
    return render(request, "spotiPY/login.html", context)


def logout_view(request):
    logout(request)
    return redirect("spotiPY:login")


def get_access_token():
    client_creds = f"{CLIENT_ID}:{CLIENT_SECRET}"
    client_creds_b64 = base64.b64encode(client_creds.encode())
    token_url = "https://accounts.spotify.com/api/token"
    token_data = {"grant_type": "client_credentials"}
    token_headers = {"Authorization": f"Basic {client_creds_b64.decode()}"}
    r = requests.post(token_url, data=token_data, headers=token_headers)
    if r.status_code not in range(200, 299):
        raise Exception("Could not authenticate client.")
    data = r.json()
    now = timezone.now()
    access_token = data["access_token"]
    expires_in = data["expires_in"]  # seconds
    expiration = now + datetime.timedelta(seconds=expires_in)
    expires = expiration < now
    if expires:
        return get_access_token()
    elif access_token == None:
        return get_access_token()
    return (access_token, expiration)


def search(request, *args, **kwargs):
    context = {}
    payload = {}
    user = request.user
    spotify_access_token = None
    results = None
    if user.is_authenticated:
        account = Account.objects.filter(email=user.email)[0]
        spotify_access_token = account.spotify_access_token
    if request.method == "GET":
        if spotify_access_token:
            query = kwargs.get("query")
            if query:
                query_params = urlencode({"q": query, "type": "artist"})
                url = f"https://api.spotify.com/v1/search?{query_params}"
                headers = {"Authorization": f"Bearer {spotify_access_token}"}
                response = requests.get(url, headers=headers)

                results = response.json()
                items = results["artists"]["items"]

                payload["artists"] = []

                for item in items[:10]:
                    dictionary = {}
                    dictionary["uri"] = item["uri"]
                    dictionary["url"] = item["external_urls"]["spotify"]
                    dictionary["followers"] = item["followers"]["total"]
                    dictionary["image_url"] = (
                        item["images"][0]["url"] if len(item["images"]) else "no-image"
                    )
                    dictionary["name"] = item["name"]
                    dictionary["popularity"] = item["popularity"]
                    payload["artists"].append(dictionary)

                payload["tracks"] = []

                for item in payload["artists"]:
                    uri = item["uri"]
                    if uri:
                        results = spotify.artist_top_tracks(uri)
                    lists = []
                    for track in results["tracks"][:10]:
                        dictionary = {}
                        if track["preview_url"]:
                            dictionary["release_date"] = track["album"]["release_date"]
                            dictionary["preview_url"] = track["preview_url"]
                            dictionary["image_url"] = (
                                track["album"]["images"][0]["url"]
                                if len(track["album"]["images"])
                                else "no-image"
                            )
                            dictionary["track"] = track["name"]
                            dictionary["url"] = track["external_urls"]["spotify"]
                            dictionary["artists"] = ", ".join(
                                name["name"] for name in track["artists"]
                            )
                            lists.append(dictionary)
                        else:
                            continue
                    if len(lists):
                        payload["tracks"].append(lists)

                    results = spotify.artist_albums(uri)
                    items = results["items"]

                    payload["album"] = []

                    for item in items[:10]:
                        dictionary = {}
                        dictionary["artists"] = ", ".join(
                            name["name"] for name in item["artists"]
                        )
                        dictionary["url"] = item["external_urls"]["spotify"]
                        dictionary["image_url"] = item["images"][0]["url"]
                        dictionary["name"] = item["name"]
                        payload["album"].append(dictionary)

                    payload["album"] = list(
                        {p["name"]: p for p in payload["album"]}.values()
                    )

                return JsonResponse(payload)
            else:
                context["no_query"] = "Query missing."
        else:
            context["no_token"] = "Authorization error."
    else:
        context["no_get"] = "Cannot get response."

    return HttpResponse(json.dumps(context), content_type="application/json")
