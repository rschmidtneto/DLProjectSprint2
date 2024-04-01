from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views import View
from collections import defaultdict
from datetime import datetime, timedelta
from .models import Client, Employee, Invoice, JobAssignment, JobRole, Job
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from .forms import bookingForm


# Create your views here.
def home(request):

# Check if the user is logged in.     
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        #authenticate user
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "You have been logged in.")
            return redirect('roaster')
        else:
            messages.success(request, "There was an error while logging in.")
            return render(request, 'home.html', {})

    else:
        return render(request, 'home.html', { })

# def login_user(request):
#     pass


def logout_user(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('home')

class RoasterView(View):

    def get(self, request, *arg, **kwargs):
        week_start_str = request.GET.get('week_start')
        selected_state = request.GET.get('state')  

        if week_start_str:
            start_week = datetime.strptime(week_start_str, '%Y-%m-%d').date()
        else:
            today = datetime.now().date()
            start_week = today - timedelta(days=today.weekday())
        end_week = start_week + timedelta(days=6)

        # Generate dates for the entire week for display purposes
        week_dates = [start_week + timedelta(days=x) for x in range(7)]

        # Fetch jobs based on the selected state
        if selected_state:
            jobs = Job.objects.filter(state=selected_state)
        else:
            jobs  = Job.objects.filter(state='NSW')

        # Fetch assignments within the specified week
        assignments = JobAssignment.objects.filter(date__range=[start_week, end_week]).select_related('job', 'employee')

        # Initialize job_assignment dictionary with all jobs, ensuring each job appears regardless of having assignments
        job_assignments = {job: [] for job in jobs}

        
        for assignment in assignments:
            if assignment.job in job_assignments:  # This check ensures that only jobs fetched above are considered
                job_assignments[assignment.job].append(assignment)
            

        context = {
            'job_assignments': job_assignments,
            'week_dates': week_dates,
            'selected_state': selected_state,
        }

        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string('roaster_table.html', context, request=request)
            return HttpResponse(html)

        return render(request, 'roaster.html', context)
    

def viewBooking(request, pk):
    schedule = get_object_or_404(JobAssignment, pk=pk)
    form = bookingForm(request.POST or None, instance=schedule)
    if request.user.is_authenticated: 
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string('booking_template.html', {'schedule':schedule, 'form':form }, request=request)
            return HttpResponse(html)
        else:
            return render(request, 'error.html', {'message': 'This action is only available via AJAX.'})
    else:
        messages.success(request, "Please log in.")
        return redirect('home')

#def createBooking(request):
    

def editBooking(request, pk):
    if request.user.is_authenticated: 
        job_assigment = get_object_or_404(JobAssignment, job_assigment_id=pk)
        if request.method == 'POST':
            if form.is_valid():
                form.save()
                return HttpResponse('Sucess')
            else:
                messages.success(request, "Ops there was an error updating this booking.")
                return HttpResponse('Error', status=400)
    else:
        messages.success(request, "Please log in.")
        return redirect('home')

def deleteBooking(request, pk):
    if request.user.is_authenticated:    
        if request.method == "POST":
            delete_it = get_object_or_404(JobAssignment, job_assignment_id=pk)
            delete_it.delete()
            messages.success(request, "Booking deleted.")
            return HttpResponse('Success')
        else:
            messages.success(request, "Ops there was an error deleting this booking.")
            return HttpResponse("Failure", status=400)
    else:
        messages.success(request, "Please log in.")
        return redirect('home')

def getEmployees(request):
    if request.user.is_authenticated:
        context = {}
        url_parameter = request.GET.get("q")

        if url_parameter:
            employees = Employee.objects.filter(name__icontains=url_parameter)
            context["employees"] = employees
            return render(request, "replace_employee.html", context=context)
        else:
            employees = Employee.objects.none()
            context["employees"] = employees

        return render(request, "get_employee.html", context=context)
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string('replace_employee.html', context, request=request)
            return HttpResponse(html)
    
    else:
        messages.success(request, "Please log in.")
        return redirect('home')
    
def getJobRoles(request, pk):
    if request.user.is_authenticated:
        jobRoles = JobRole.objects.filter(job_id=pk)  
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string('jobrole_replace.html', {'jobRoles': jobRoles}, request=request)
            return HttpResponse(html)
        else:
            jobRoles = JobRole.objects.filter(job_role_id=pk)
            print(jobRoles)
            return render(request, 'jobrole.html', {'jobRoles': jobRoles})
            
    else:
        messages.success(request, "Please log in.")
        return redirect('home')