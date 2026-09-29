import re
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class UserLogin(UserCreationForm):
    username = forms.CharField(label="Phone Number")

    def clean_username(self):
        phone = self.cleaned_data['username']

        if not re.fullmatch(r'[6-9]\d{9}', phone):
            raise forms.ValidationError("Enter valid 10-digit phone number")

        return phone

    class Meta:
        model = User
        fields = ('username', 'password1', 'password2')
