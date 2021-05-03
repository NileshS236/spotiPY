from django.urls import path

from .views import *

app_name = "spotiPY"

urlpatterns = [
    path("", home_view, name="home"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("signup/", signup_view, name="signup"),
    path("search/<query>/", search, name="search"),
]
