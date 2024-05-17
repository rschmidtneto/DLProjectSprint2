from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator
from django.contrib import messages
from django.views import View
from collections import defaultdict
from datetime import datetime, timedelta
from .models import Client, Employee, Invoice, JobAssignment, JobRole, Job, Timesheet, InvoiceStaff
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.contrib.auth.forms import PasswordChangeForm
from decimal import Decimal
from .forms import AddJobForm, EmployeeForm, JobRoleForm


def home(request):

    """
    Handles user login. POST to authenticate, GET to serve login page.

    """    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        #authenticate user
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, "You have been logged in.")
            return redirect('roster')
        else:
            messages.error(request, "There was an error while logging in.")
            return render(request, 'login.html', {})

    else:
        return render(request, 'login.html', { })



def logout_user(request):
    """
    Logs out the user and redirects to home.

    """
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('home')

class RosterView(View):
    """
    Displays roster for jobs assigned within a week, filtered by state.
    Handles both AJAX and normal requests.

    """

    def get(self, request, *arg, **kwargs):
        week_start_str = request.GET.get('week_start')
        selected_state = request.GET.get('state')  

        if week_start_str:
            start_week = datetime.strptime(week_start_str, '%Y-%m-%d').date()
            end_week = start_week + timedelta(days=6)
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

        if selected_state:
            state = selected_state
        else:
            state = "NSW"


        context = {
            'job_assignments': job_assignments,
            'week_dates': week_dates,
            'selected_state': selected_state,
            'start_week': start_week,
            'end_week':end_week,
            'state': state
        }

        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string('roster_table.html', context, request=request)
            return HttpResponse(html)

        return render(request, 'roster.html', context)
    

def viewBooking(request, pk):
    """
    View or edit an existing booking.
    
    """
    schedule = get_object_or_404(JobAssignment, pk=pk)
    date_obj = schedule.date
    jobId_obj= schedule.job_id
    jobRoles = JobRole.objects.filter(job_id=schedule.job_id)

    if request.user.is_authenticated: 
        html = render_to_string('edit_booking.html', {'jobId_obj' : jobId_obj, 'date_obj':date_obj, 'jobRoles':jobRoles, 'schedule':schedule }, request=request)
        return HttpResponse(html)
        
    else:
        messages.success(request, "Please log in.")
        return redirect('home')
    
    

def addBooking(request, jobId, date):
    """
    GET to add a new booking.
    
    """
    date_obj = datetime.strptime(date, '%Y-%m-%d').date()
    jobId_obj= Job.objects.get(job_id=jobId)
    jobRoles = JobRole.objects.filter(job_id=jobId) 
    if request.user.is_authenticated: 
        html = render_to_string('add_booking.html', {'jobId_obj' : jobId_obj, 'date_obj':date_obj, 'jobRoles':jobRoles }, request=request)
        return HttpResponse(html)
        
    else:
        messages.success(request, "Please log in.")
        return redirect('home')
    
def createBooking(request):
    """
    POST to create a new booking.
    
    """
    if request.user.is_authenticated: 
        if request.method == "POST":
            jobId = request.POST.get('jobid')
            employeeId = request.POST.get('employeeid')
            jobRoleId = request.POST.get('jobRoleid')
            dateStr = request.POST.get('date')
            date = datetime.strptime(dateStr, '%Y-%m-%d').date()
            notes = request.POST.get('notes')
            
            # Fetch model instances
            try:
                job = Job.objects.get(pk=jobId)
                employee = Employee.objects.get(pk=employeeId)
                jobRole = JobRole.objects.get(pk=jobRoleId)
                
                JobAssignment.objects.create(job=job, employee=employee, job_role=jobRole, date=date, notes=notes)
                employee.days_worked += 1
                employee.save()

                return HttpResponse('Success')
            except (Job.DoesNotExist, Employee.DoesNotExist, JobRole.DoesNotExist) as e:
                return HttpResponse(f'Error: {e}', status=400)
        else:
            return HttpResponse('Request must be POST', status=400)
    else:
        return HttpResponse('Unauthorized', status=401)



    

def editBooking(request, pk):
    """
    POST to edit a booking.
    
    """
    
    if not request.user.is_authenticated:
        return HttpResponse('Unauthorized', status=401)
    
    if request.method != "POST":
        return HttpResponse('Request must be POST', status=400)

    # Fetch the JobAssignment instance by pk
    job_assignment = get_object_or_404(JobAssignment, pk=pk)
    old_employee = job_assignment.employee
    # Update fields from POST data if available
    employee_id = request.POST.get('employeeid')
    job_role_id = request.POST.get('jobRoleid')
    notes = request.POST.get('notes')

    try:
        if employee_id and int(employee_id) != old_employee.employee_id:
            new_employee = Employee.objects.get(pk=employee_id)
            job_assignment.employee = new_employee
            old_employee.days_worked -= 1
            old_employee.save()
            new_employee.days_worked += 1
            new_employee.save()

        if job_role_id:
            job_role = JobRole.objects.get(pk=job_role_id)
            job_assignment.job_role = job_role  # Update the job role
        #Save notes
        job_assignment.notes = notes
        # Save the updated job_assignment
        job_assignment.save()
        return HttpResponse('Success')

    except (Employee.DoesNotExist, JobRole.DoesNotExist) as e:
        return HttpResponse(f'Error: {e}', status=400)
    
    

def deleteBooking(request, pk):
    """
    POST to delete a booking.
    
    """
    if request.user.is_authenticated:    
        if request.method == "POST":
            job_assignment = get_object_or_404(JobAssignment, pk=pk)
            employee = job_assignment.employee
            job_assignment.delete()
            employee.days_worked -= 1
            employee.save()
            #messages.success(request, "Booking deleted.")
            return HttpResponse('Success')
        else:
            messages.error(request, "Ops there was an error deleting this booking.")
            return HttpResponse("Failure", status=400)
    else:
        messages.success(request, "Please log in.")
        return redirect('home')

def getEmployees(request):
    """
    GET to search employees on the database and return succeful response to ajax.
    
    """
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
    """
    GET to search job roles on the database and return it to the dropdown menus.
    
    """
    if request.user.is_authenticated:
        jobRoles = JobRole.objects.filter(job_id=pk)  
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string('jobrole_replace.html', {'jobRoles': jobRoles}, request=request)
            print("response was sent to ajax from getJobRoles")
            return HttpResponse(html)
        else:
            jobRoles = JobRole.objects.filter(job_role_id=pk)
            return HttpResponse("Not an ajax request")
            
    else:
        messages.success(request, "Please log in.")
        return redirect('home')
    

def change_password(request):
    """
    POST form to change the password
    
    """
    if request.user.is_authenticated:
        if request.method == 'POST':
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                user = form.save()
                update_session_auth_hash(request, user)  
                messages.success(request, 'Your password was successfully updated!')
                return redirect('roster')
            else:
                messages.error(request, 'Please correct the error below.')
        else:
            form = PasswordChangeForm(request.user)
        return render(request, 'change_password.html', {
            'form': form })
    else:
        return redirect('home')
        

#sprint 2

def loadRoles(request, pk):
    """
    GET jobs, load the form to update the job and search job roles on the database and return it to add or delete from jobs.
    
    """
    job = Job.objects.prefetch_related('jobrole_set').get(job_id=pk)
    form = AddJobForm(instance=job)
    formRole = JobRoleForm()

    context = {
        'job': job,
        'form': form,
        'formRole':formRole
    }
    if request.user.is_authenticated:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string('jobs_table.html', context, request=request)
            return HttpResponse(html)
        else:
            return HttpResponse('Unauthorized', status=401)
            
    else:
        messages.success(request, "Please log in.")
        return redirect('home')
    

    
def deleteJobRole(request, pk):
    """
    POST to delete a job role.
    
    """
    if request.user.is_authenticated:    
        if request.method == "POST":
            delete_it = get_object_or_404(JobRole, job_role_id=pk)
            delete_it.delete()
            #messages.success(request, "Booking deleted.")
            return HttpResponse('Success')
        else:
            messages.error(request, "Ops there was an error deleting this job role.")
            return HttpResponse("Failure", status=400)
    else:
        messages.success(request, "Please log in.")
        return redirect('home')
    
def createJobRole(request, pk):
    """
    POST to create a new Job Role to a specific job.
    """

    if not request.user.is_authenticated:
        return HttpResponse('Unauthorized', status=401)

    if request.method == "POST":
        job = get_object_or_404(Job, job_id=pk)
        
        # Create a form instance with POST data
        formRole = JobRoleForm(request.POST)
        
        if formRole.is_valid():
            job_role = formRole.save(commit=False)
            job_role.job = job
            job_role.save()
            return JsonResponse({'message': 'Job role created successfully'})
        else:
            return JsonResponse({'errors': formRole.errors}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

    

def add_job(request):
    """
    View to display the form to add a new job and handle the POST request to create a new job.

    """
    if request.user.is_authenticated:
        if request.method == 'POST':
            form = AddJobForm(request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, "Job Saved, do not forget to add at least one job role.")
                return redirect('roster')
        else:
            form = AddJobForm()
        return render(request, 'add_job.html', {'form': form})
    
def editJob(request, pk):
    """
    POST to edit a job role.
    
    """
    job = Job.objects.get(job_id=pk)
    if request.user.is_authenticated:
        if request.method == 'POST':
            form = AddJobForm(request.POST, instance=job)
            if form.is_valid():
                form.save()
                return JsonResponse({'success': True, 'message': 'Job details updated successfully!'})
            else: 
                return JsonResponse({'success': False, 'form_errors': form.errors.as_json()}, status=400) 

    else:
        messages.success(request, "Please log in.")
        return redirect('home')
    
def deleteJob(request, pk):
    """
    POST to delete a job role.
    
    """
    if request.user.is_authenticated:    
        if request.method == "POST":
            delete_it = get_object_or_404(Job, job_id=pk)
            delete_it.delete()
            #messages.success(request, "Job and all related job roles deleted.")
            return HttpResponse('Success')
        else:
            messages.error(request, "Ops there was an error deleting this job.")
            return HttpResponse("Failure", status=400)
    else:
        messages.success(request, "Please log in.")
        return redirect('home')


def Employees(request):

    """
    View to display the employee page, and also handles a GET response for the search bar using AJAX to reload part of the page.
    """

    if request.user.is_authenticated:
        context = {}
        url_parameter = request.GET.get("q")
        filters = {
        'general_labour': request.GET.get("general_labour") == 'true',
        'traffic_controller': request.GET.get("traffic_controller") == 'true',
        'first_aider': request.GET.get("first_aider") == 'true',
        'construction_cleaner': request.GET.get("construction_cleaner") == 'true',
        'boom_lift': request.GET.get("boom_lift") == 'true',
        'telehandler': request.GET.get("telehandler") == 'true',
        'forklift_driver': request.GET.get("forklift_driver") == 'true',
        'hoister_driver': request.GET.get("hoister_driver") == 'true'
        }

        if url_parameter:
            employees = Employee.objects.filter(name__icontains=url_parameter)
        else:
            #employees = Employee.objects.filter(name__startswith='A') Maybe use this for prod, as there will be many employees.
            employees = Employee.objects.all()
        for key, value in filters.items():
            if value:
                employees = employees.filter(**{key: True})

        context["employees"] = employees

        # Check if it's an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string('employee_table.html', context, request=request)
            return HttpResponse(html)
        else:
            # Render the full employee page if not an AJAX request
            return render(request, "employee.html", context=context)
    
    else:
        messages.success(request, "Please log in.")
        return redirect('login')
    
def manage_employee(request, employee_id=None):
    """
    View to edit or add a new employee.
    """
    if not request.user.is_authenticated:
        messages.error(request, "Please log in.")
        return redirect('login')

    if request.method == 'POST':
        if employee_id:
            employee = get_object_or_404(Employee, pk=employee_id)
            form = EmployeeForm(request.POST, instance=employee)
        else:
            form = EmployeeForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Employee saved.")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return HttpResponse('Success')  
            else:
                return redirect('Employees')
        else:
            # Form is invalid, so return the form with errors (handle AJAX and regular requests differently)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                html = render_to_string('manage_employee.html', {'form': form}, request=request)
                return HttpResponse(html, status=400)  # 400 Bad Request for AJAX
            else:
                return render(request, 'manage_employee.html', {'form': form})  # Regular request with errors

    else:  # Handle GET requests
        if employee_id:
            employee = get_object_or_404(Employee, pk=employee_id)
            form = EmployeeForm(instance=employee)
        else:
            form = EmployeeForm()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string('manage_employee.html', {'form': form}, request=request)
            return HttpResponse(html)
        else:
            return render(request, 'manage_employee.html', {'form': form})
        
class EmployeeAssignmentView(View):
    """
    Displays employee-specific job assignments, it can be filtered by state or week.
    Handles both AJAX and normal requests.
    """
    

        
    def get(self, request, *args, **kwargs):
        week_start_str = request.GET.get('week_start')
        selected_state = request.GET.get('state')
        if not request.user.is_authenticated:
            messages.error(request, "Please log in.") 
            return redirect('login')

        # Calculate start and end of the week
        if week_start_str:
            start_week = datetime.strptime(week_start_str, '%Y-%m-%d').date()
            end_week = start_week + timedelta(days=6)
        else:
            today = datetime.now().date()
            start_week = today - timedelta(days=today.weekday())
            end_week = start_week + timedelta(days=6)

        # Fetch job assignments within the specified week and optionally filter by state
        query = JobAssignment.objects.filter(date__range=[start_week, end_week])
        if selected_state:
            query = query.filter(job__state=selected_state)

       # Organize job assignments by employee and check if hours worked already been entered on the system. 
        employee_assignments = {}
        for assignment in query.select_related('employee', 'job', 'job_role'):
            emp = assignment.employee
            if emp not in employee_assignments:
                employee_assignments[emp] = {
                    'assignments': [],
                    'all_times_entered': True  # Assume true until proven otherwise
                }
            employee_assignments[emp]['assignments'].append(assignment)
            # Check if all required times are entered
            if not (assignment.start_time and assignment.finish_time and assignment.lunch_hours is not None):
                employee_assignments[emp]['all_times_entered'] = False

        context = {
            'employee_assignments': employee_assignments,
            'week_start': start_week,
            'selected_state': selected_state,
        }

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string('assignment_table.html', context, request=request)
            return HttpResponse(html)

        return render(request, 'employee_assignments.html', context)
    
class EmployeeDetailsView(View):
    """
    Displays employee-specific job assignments, will handle AJAX get request
    
    """

    def get(self, request, employee_id, *args, **kwargs):
        week_start_str = request.GET.get('week_start')
        if week_start_str:
            start_week = datetime.strptime(week_start_str, '%Y-%m-%d').date()
        else:
            # Default to current week if no date is provided
            today = datetime.now().date()
            start_week = today - timedelta(days=today.weekday())

        end_week = start_week + timedelta(days=6)

        assignments = JobAssignment.objects.filter(
            employee_id=employee_id,
            date__range=(start_week, end_week)
        ).select_related('job_role')

        context = {
            'assignments': assignments,
            'week_start': start_week,
            'employee_id': employee_id
        }
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string('employee_details_assignment.html', context, request=request)
            return HttpResponse(html)

        return HttpResponse("This view is intended for AJAX requests only.")
    
class UpdateHours(View):
    """
    Will update hours for the job assignmets, it will only handle AJAX post requests
    
    """
    
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.method == "POST":
                for key in request.POST:
                    if key.startswith('assignment_id_'):
                        index = key.split('_')[-1]
                        assignment_id = request.POST.get(key)
                        start_time = request.POST.get('start_time_' + index)
                        finish_time = request.POST.get('finish_time_' + index)
                        lunch_hours = request.POST.get('lunch_hours_' + index)
                        worked_hours = request.POST.get('worked_hours_' + index)
                        regular_hours = request.POST.get('regular_hours_' + index)
                        overtime_1_5x = request.POST.get('overtime_1_5x_' + index)
                        overtime_2x = request.POST.get('overtime_2x_' + index)
                        total_pay = request.POST.get('total_pay_' + index)
                    

                        assignment = get_object_or_404(JobAssignment, pk=assignment_id)
                        assignment.start_time = datetime.strptime(start_time, '%H:%M').time()
                        assignment.finish_time = datetime.strptime(finish_time, '%H:%M').time()
                        assignment.lunch_hours = Decimal(lunch_hours)
                        assignment.worked_hours = Decimal(worked_hours)
                        assignment.regular_hours = Decimal(regular_hours)
                        assignment.timeandhalf_hours = Decimal(overtime_1_5x)
                        assignment.double_hours = Decimal(overtime_2x)
                        assignment.total_cost = Decimal(total_pay)
                        assignment.times_entered = True
                        assignment.save()
                return HttpResponse('Success')
            else:
                return HttpResponse("Ops, there was an error saving the hours for this job assignment.", status=400)
        else:
            return redirect('home')


def postTimesheet(request):
        if request.user.is_authenticated:
            if request.method == "POST":
                employee_id = request.POST.get('employee_id')
                week_start = request.POST.get('week_start')
                timesheet_file = request.FILES.get('timesheet_file')
                assignment_ids = request.POST.getlist('assignment_ids')  


                employee = get_object_or_404(Employee, employee_id=employee_id)
                timesheet = Timesheet(employee=employee, week_start=week_start, timesheet_file=timesheet_file)
                timesheet.save()

                # Link each assignment to the timesheet
                for assignment_id in assignment_ids:
                    assignment = JobAssignment.objects.get(job_assignment_id=assignment_id)
                    timesheet.job_assignments.add(assignment)

                timesheet.save()
                return HttpResponse('Timesheet saved')

            else:
                return HttpResponse("Ops, there was an error saving the timesheet.", status=400)
        else:
            return redirect('home')
        
def postInvoiceStaff(request):
        if request.user.is_authenticated:
            if request.method == "POST":
                employee_id = request.POST.get('employee_id')
                week_start = request.POST.get('week_start')
                timesheet_file = request.FILES.get('invoice_file')
                assignment_ids = request.POST.getlist('assignment_ids')  

                employee = get_object_or_404(Employee, employee_id=employee_id)
                invoice = InvoiceStaff(employee=employee, week_start=week_start, invoice_file=timesheet_file)
                invoice.save()

                # Link each assignment to the timesheet
                for assignment_id in assignment_ids:
                    assignment = JobAssignment.objects.get(job_assignment_id=assignment_id)
                    invoice.job_assignments.add(assignment)

                invoice.save()
                return HttpResponse('Invoice saved')

            else:
                return HttpResponse("Ops, there was an error saving the this invoice.", status=400)
        else:
            return redirect('home')
        

class InvoiceAssignmentView(View):
    """
    Displays job-specific job assignments, it can be filtered by state or week, getting ready to create the invoice
    Handles both AJAX and normal requests.
    """
    

        
    def get(self, request, *args, **kwargs):
        week_start_str = request.GET.get('week_start')
        period_end_str = request.GET.get('period_end')
        selected_state = request.GET.get('state')

        if not request.user.is_authenticated:
            messages.error(request, "Please log in.") 
            return redirect('login')

        # Calculate start and end of the week
        if week_start_str and period_end_str:
            start_week = datetime.strptime(week_start_str, '%Y-%m-%d').date()
            period_end = datetime.strptime(period_end_str, '%Y-%m-%d').date()

        elif week_start_str:
            start_week = datetime.strptime(week_start_str, '%Y-%m-%d').date()
            period_end = start_week + timedelta(days=6)

        else:
            today = datetime.now().date()
            start_week = today - timedelta(days=today.weekday())
            period_end = start_week + timedelta(days=6)

        # Fetch job assignments within the specified week and optionally filter by state
        query = JobAssignment.objects.filter(date__range=[start_week, period_end])
        if selected_state:
            query = query.filter(job__state=selected_state)

       # Organize job assignments by PO NAme and check if hours worked already been entered on the system and the invoice has been sent.  
        job_assignments = {}
       
        for assignment in query.select_related('employee', 'job', 'job_role'):
            job_po = assignment.job.po_name
            job_id =assignment.job.job_id
            # Initialize the dictionary for this job PO if it doesn't exist
            if job_po not in job_assignments:
                job_assignments[job_po] = {
                    'assignments': [],
                    'all_times_entered': True,  # Assume true until proven otherwise
                    'invoiced' : True, # Assume false until proven otherwise
                    'job_id': job_id
                }

            # Append this assignment to the job PO's list
            job_assignments[job_po]['assignments'].append(assignment)

            # Check if times are not fully entered
            if not assignment.times_entered:
                job_assignments[job_po]['all_times_entered'] = False

            # Check if the job is already invoiced
            if not assignment.invoiced:
                job_assignments[job_po]['invoiced'] = False

        context = {
            'job_assignments': job_assignments,
            'week_start': start_week,
            'period_end': period_end,
            'selected_state': selected_state,
        }

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string('invoice_table.html', context, request=request)
            return HttpResponse(html)

        return render(request, 'invoice_page.html', context)        
        
class InvoiceView(View):
    """
    Displays table with job assignments getting ready to create the invoice, will handle AJAX get request
    
    """

    def get(self, request, job_id, *args, **kwargs):
        week_start_str = request.GET.get('week_start')
        period_end_str = request.GET.get('period_end')

        if not request.user.is_authenticated:
            messages.error(request, "Please log in.") 
            return redirect('login')

        # Calculate start and end of the week
        if week_start_str and period_end_str:
            start_week = datetime.strptime(week_start_str, '%Y-%m-%d').date()
            period_end = datetime.strptime(period_end_str, '%Y-%m-%d').date()

        elif week_start_str:
            start_week = datetime.strptime(week_start_str, '%Y-%m-%d').date()
            period_end = start_week + timedelta(days=6)

        else:
            today = datetime.now().date()
            start_week = today - timedelta(days=today.weekday())
            period_end = start_week + timedelta(days=6)
        
        duedate = period_end + timedelta(days=4)
        invoice_id = Invoice.objects.latest('invoice_id').invoice_id 
        invoice_id = invoice_id + 1
        job = get_object_or_404(Job, job_id=job_id)
        client = job.client

        assignments = JobAssignment.objects.filter(
            job_id=job_id,
            date__range=(start_week, period_end)
        ).select_related('employee', 'job', 'job_role')
        
        # Filter out assignments based on conditions
        assignments = [assignment for assignment in assignments if assignment.times_entered and not assignment.invoiced]

            

        context = {
            'assignments': assignments,
            'duedate': duedate,
            'week_start': start_week,
            'period_end': period_end,
            'job': job,
            'invoice_id': invoice_id,
            'client' : client
        }

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string('invoice_details.html', context, request=request)
            return HttpResponse(html)

        return HttpResponse("This view is intended for AJAX requests only.")
    


class saveInvoice(View):
    """
    Save the data for the invoice database, it will only handle AJAX post requests
    
    """
    
    def post(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.method == "POST":
                job_id = request.POST.get('job_id')
                due_date_str = request.POST.get('due_date')
                from_date_str = request.POST.get('invoice_from_date')
                to_date_str = request.POST.get('invoce_to_date')
                total = request.POST.get('invoice_subtotal')
                worked_hours = request.POST.get('total_worked_hours')
                regular_hours = request.POST.get('total_regular_hours')
                timeandhalf_hours = request.POST.get('total_1_5x_hours')
                double_hours = request.POST.get('total_2x_hours')
                invoice_total = request.POST.get('invoice_total')
                gst = request.POST.get('gst')
                cost = request.POST.get('cost-total')
        

                due_date = datetime.strptime(due_date_str, '%d/%m/%Y').date()
                from_date = datetime.strptime(from_date_str, '%d/%m/%Y').date()
                to_date = datetime.strptime(to_date_str, '%d/%m/%Y').date()
                
                job = get_object_or_404(Job, job_id=job_id)

                invoice = Invoice.objects.create(
                    job = job,
                    due_date = due_date,
                    from_date = from_date,
                    to_date = to_date,
                    total = Decimal(total),
                    worked_hours = Decimal(worked_hours),
                    regular_hours = Decimal(regular_hours),
                    timeandhalf_hours = Decimal(timeandhalf_hours),
                    double_hours = Decimal(double_hours),
                    invoice_total = Decimal(invoice_total),
                    gst = Decimal(gst),
                    cost= Decimal(cost),
                    profit = Decimal(total) - Decimal(cost),
                )
                # Change status of the job assingment to invoiced, to avoid the same shift being charged more than 1 time, and save it to the invoice. 
                for key,value in request.POST.items():
                    if key.startswith('assignment_id_'):
                        assignment_id = value
                        assignment = get_object_or_404(JobAssignment, pk=assignment_id)
                        assignment.invoiced = True
                        invoice.job_assignments.add(assignment)
                        assignment.save()

                invoice.save()
                return HttpResponse('Success')
            else:
                return HttpResponse("Ops, there was an error saving this invoice.", status=400)
        else:
            return redirect('home')
        

def invoice_list(request):
    """
    Create the table to display info about all invoices for the manage invoice page.
    
    """


    invoices_list = Invoice.objects.all().order_by('-invoice_id')
    paginator = Paginator(invoices_list, 10) #show 10 lines of invoices, edit if nescessary. 

    page_number = request.GET.get('page')
    invoices = paginator.get_page(page_number)

    return render(request, 'invoice_manage.html', {'invoices':invoices})

def view_invoice(request, pk):
    """
    Get a ajax request to display details about specific invoice number, the user then can update it or delete it. 
    
    """
    if request.user.is_authenticated:
        invoice = get_object_or_404(Invoice, invoice_id=pk)
        job = invoice.job
        client = job.client
        assignments = invoice.job_assignments.all()

        context = {
            'client': client,
            'invoice': invoice,
            'job': job,
            'assignments': assignments
        }

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            html = render_to_string('invoice_update.html', context, request=request)
            return HttpResponse(html)
        else:
            return HttpResponse("Ops, there was an error loading this invoice.", status=400)
    else:
            return redirect('home')
    
def updateInvoice(request, pk ):
        if request.user.is_authenticated:
            if request.method == "POST":
                due_date_str = request.POST.get('due_date')
                from_date_str = request.POST.get('invoice_from_date')
                to_date_str = request.POST.get('invoice_to_date')
                subtotal = request.POST.get('subtotal')
                worked_hours = request.POST.get('total_worked_hours')
                regular_hours = request.POST.get('total_regular_hours')
                timeandhalf_hours = request.POST.get('total_1_5x_hours')
                double_hours = request.POST.get('total_2x_hours')
                invoice_total = request.POST.get('total_aud')
                gst = request.POST.get('gst')
                cost = request.POST.get('cost-total')
        

                due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
                to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
                
                

                invoice = get_object_or_404(Invoice, invoice_id = pk)
                invoice.due_date = due_date
                invoice.from_date = from_date
                invoice.to_date = to_date
                invoice.total = Decimal(subtotal)
                invoice.worked_hours = Decimal(worked_hours)
                invoice.regular_hours = Decimal(regular_hours)
                invoice.timeandhalf_hours = Decimal(timeandhalf_hours)
                invoice.double_hours = Decimal(double_hours)
                invoice.invoice_total = Decimal(invoice_total)
                invoice.gst = Decimal(gst)
                invoice.cost= Decimal(cost)
                invoice.profit = Decimal(subtotal) - Decimal(cost)
               
    
                # Change status of the job assingment to invoiced, to avoid the same shift being charged more than 1 time, and save it to the invoice. 
                for key,value in request.POST.items():
                    if key.startswith('assignment_id_'):
                        assignment_id = value
                        assignment = get_object_or_404(JobAssignment, pk=assignment_id)
                        assignment.invoiced = True
                        invoice.job_assignments.add(assignment)
                        assignment.save()

                invoice.save()
                return HttpResponse('Success')
            else:
                return HttpResponse("Ops, there was an error saving this invoice.", status=400)
        else:
            return redirect('home')
        
@login_required
@require_POST  # Ensures that this view can only be accessed via POST method
def deleteInvoice(request, pk):
    """
    POST to delete an invoice.
    """
    try:
        invoice = get_object_or_404(Invoice, pk=pk)

        #Check if the request.user has specific permissions to delete the invoice
        if not request.user.has_perm('invoice.delete_invoice', invoice):
            messages.error(request, "You do not have permission to delete this invoice.")
            return redirect('invoice-list')

        invoice.delete()
        messages.success(request, "Invoice deleted.")
        return redirect('invoice-list') 
    except Exception as e:
        messages.error(request, "There was an error trying to delete this invoice: %s" % e)
        return redirect('invoice-list')