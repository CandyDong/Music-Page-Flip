from django import forms

from django.contrib.auth.models import User
from django.contrib.auth import authenticate

from pageFlipper.models import Score

MAX_UPLOAD_SIZE = 2500000

class LoginForm(forms.Form):
    username = forms.CharField(max_length = 20, widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'Username', 'id': 'username'}))
    password = forms.CharField(max_length = 200, widget = forms.PasswordInput(
        attrs={'class': 'form-control', 'placeholder': 'Password', 'id': 'password'}))

    # Customizes form validation for properties that apply to more
    # than one field.  Overrides the forms.Form.clean function.
    def clean(self):
        # Calls our parent (forms.Form) .clean function, gets a dictionary
        # of cleaned data as a result
        cleaned_data = super().clean()

        # Confirms that the two password fields match
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        user = authenticate(username=username, password=password)
        if not user:
            raise forms.ValidationError("Invalid username/password")

        # We must return the cleaned data we got from our parent.
        return cleaned_data

class RegistrationForm(forms.Form):
    username   = forms.CharField(max_length = 20)
    password   = forms.CharField(max_length = 200, 
                                 label='Password', 
                                 widget = forms.PasswordInput())
    confirm_password  = forms.CharField(max_length = 200, 
                                 label='Confirm password',  
                                 widget = forms.PasswordInput())


    # Customizes form validation for properties that apply to more
    # than one field.  Overrides the forms.Form.clean function.
    def clean(self):
        # Calls our parent (forms.Form) .clean function, gets a dictionary
        # of cleaned data as a result
        cleaned_data = super().clean()

        # Confirms that the two password fields match
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords did not match.")

        # We must return the cleaned data we got from our parent.
        return cleaned_data


    # Customizes form validation for the username field.
    def clean_username(self):
        # Confirms that the username is not already present in the
        # User model database.
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__exact=username):
            raise forms.ValidationError("Username is already taken.")

        # We must return the cleaned data we got from the cleaned_data
        # dictionary
        return username

class ScoreForm(forms.ModelForm):
    class Meta:
        model = Score
        fields = ('pic',)

    def clean_picture(self):
        pic = self.cleaned_data['pic']
        if not pic:
            raise forms.ValidationError('You must upload a pic')
        if not pic.content_type or not pic.content_type.startswith('image'):
            raise forms.ValidationError('File type is not image')
        if pic.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError('File too big (max size is {0} bytes)'.format(MAX_UPLOAD_SIZE))
        return pic
