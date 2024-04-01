from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms
from .models import Client, Employee, Invoice, JobAssignment, JobRole, Job




class bookingForm(forms.ModelForm):
    job = forms.CharField(required=True, widget=forms.widgets.TextInput(attrs={"class":"form-control"}), label="")
    employee = forms.CharField(required=True, widget=forms.widgets.TextInput(attrs={"class":"form-control"}), label="")
    job_role = forms.CharField(required=True, widget=forms.widgets.TextInput(attrs={"class":"form-control"}), label="")
    date = forms.CharField(required=True, widget=forms.widgets.TextInput(attrs={"class":"form-control"}), label="")
    

    class Meta:
        model = JobAssignment
        exclude = ("user",)