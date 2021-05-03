from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm

from .models import Account


class AccountRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        label="Email", help_text="Required. Please enter a valid email."
    )

    class Meta:
        model = Account
        fields = ("email", "username", "password1", "password2")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        try:
            account = Account.objects.get(email=email)
        except:
            return email
        raise forms.ValidationError(f"Email {email} already exists.")

    def clean_username(self):
        username = self.cleaned_data["username"]
        try:
            account = Account.objects.get(username=username)
        except:
            return username
        raise forms.ValidationError(f"Username {username} already exists.")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords don't match")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class AccountAuthenticationForm(forms.ModelForm):
    password = forms.CharField(label="Password", widget=forms.PasswordInput)

    class Meta:
        model = Account
        fields = ("email", "password")

    def clean(self):
        if self.is_valid():
            email = self.cleaned_data["email"]
            password = self.cleaned_data["password"]
            if not authenticate(email=email, password=password):
                raise forms.ValidationError("Invalid Input!")