from django.contrib import admin
from .models import Client, Employee, Invoice, JobAssignment, JobRole, Job

admin. site.register(Client)
admin. site.register(Employee)
admin. site.register(Invoice)
admin. site.register(JobAssignment)
admin. site.register(JobRole)
admin. site.register(Job)
