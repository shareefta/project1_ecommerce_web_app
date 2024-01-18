import re

from django import forms
from .models import Account, AccountUser, UserProfile, Address
from django.core.validators import MinLengthValidator

class RegistrationForm(forms.ModelForm):
    phone_number = forms.CharField(widget=forms.TextInput())

    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder' : 'Enter Password'
    }))

    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Confirm Password'
    }))
    class Meta:
        model = Account
        fields = ['first_name', 'last_name', 'email', 'password']


    def __init__(self, *args, **kwargs):
        super(RegistrationForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].widget.attrs['placeholder'] = 'Enter First Name'
        self.fields['last_name'].widget.attrs['placeholder'] = 'Enter Last Name'
        self.fields['email'].widget.attrs['placeholder'] = 'Enter Email Address'
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'

    def clean(self):
        cleaned_data = super(RegistrationForm, self).clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password != confirm_password:
            raise forms.ValidationError(
                "Password does not match"
            )

            # Validate password strength
        if not re.match(r'^(?=.*[a-zA-Z])(?=.*\d).{8,}$', password):
            raise forms.ValidationError(
                "Password should be a minimum of 8 characters and include both letters and numbers"
            )


    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not first_name or first_name.isspace():
            raise forms.ValidationError("First Name cannot be empty or contain only white spaces.")
        return first_name.strip()

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if not last_name or last_name.isspace():
            raise forms.ValidationError("Last Name cannot be empty or contain only white spaces.")
        return last_name.strip()

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if not phone_number or phone_number.isspace():
            raise forms.ValidationError("Phone number cannot be empty or contain only white spaces.")
        return phone_number.strip()

class UserForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ('first_name', 'last_name')

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'

class UserProfileForm(forms.ModelForm):
    profile_picture = forms.ImageField(required=False, error_messages={'invalid': ("Image File Only")}, widget=forms.FileInput)
    class Meta:
        model = UserProfile
        fields = ('phone_number', 'address_line_1', 'address_line_2', 'city', 'state', 'country', 'profile_picture')

    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = ('full_name', 'phone_number', 'address_line_1', 'address_line_2', 'city', 'state', 'country', 'zipcode')

    def __init__(self, *args, **kwargs):
        super(AddressForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'


class UserRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder' : 'Enter Password'
    }))

    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Confirm Password'
    }))
    class Meta:
        model = AccountUser
        fields = ['full_name', 'email', 'phone_number', 'password']


    def __init__(self, *args, **kwargs):
        super(UserRegistrationForm, self).__init__(*args, **kwargs)
        self.fields['full_name'].widget.attrs['placeholder'] = 'Enter Your Name'
        self.fields['email'].widget.attrs['placeholder'] = 'Enter Email Address'
        self.fields['phone_number'].widget.attrs['placeholder'] = 'Enter Mobile Number'
        for field in self.fields:
            self.fields[field].widget.attrs['class'] = 'form-control'

    def clean_full_name(self):
        full_name = self.cleaned_data.get('full_name')
        if not full_name or full_name.isspace():
            raise forms.ValidationError("Name cannot be empty or contain only white spaces.")
        return full_name.strip()

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if not phone_number or phone_number.isspace():
            raise forms.ValidationError("Phone number cannot be empty or contain only white spaces.")
        return phone_number.strip()

        #     # Validate phone number format
        # if not re.match(r'^\d{10}$', phone_number):
        #     raise forms.ValidationError(
        #         "Invalid phone number format. Please enter a 10-digit number"
        #     )


    def clean(self):
        cleaned_data = super(UserRegistrationForm, self).clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password != confirm_password:
            raise forms.ValidationError(
                "Password does not match"
            )

            # Validate password strength
        if not re.match(r'^(?=.*[a-zA-Z])(?=.*\d).{8,}$', password):
            raise forms.ValidationError(
                "Password should be a minimum of 8 characters and include both letters and numbers"
            )
