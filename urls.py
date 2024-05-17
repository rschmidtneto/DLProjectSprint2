
from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    #sprint1
    path('',views.home, name='home'),
    #path('',views.login_user, name='login'),
    path('logout/',views.logout_user, name='logout'),
    path('roster/', views.RosterView.as_view(), name='roster'),
    path('roster/booking/<int:pk>', views.viewBooking, name = 'booking'),
    path('edit/<int:pk>', views.editBooking, name = 'editBooking'),
    path('delete/<int:pk>', views.deleteBooking, name = 'deleteBooking'),
    path('addBooking/<int:jobId>/<str:date>/', views.addBooking, name = 'addBooking'),
    path('employees/', views.getEmployees, name = 'getEmployees'),
    path('getJobRoles/<int:pk>', views.getJobRoles, name = 'getJobRoles'),
    path('create/', views.createBooking, name = 'createBooking'),
    path('change-password/', views.change_password, name='change_password'),
    #sprint2
    path('roster/loadRoles/<int:pk>', views.loadRoles, name = 'loadRoles'),
    path('deleteJobRole/<int:pk>', views.deleteJobRole, name = 'deleteJobRole'),
    path('createJobRoles/<int:pk>', views.createJobRole, name = 'createJobRole'),
    path('addJob/', views.add_job, name = 'addJob'),
    path('edit-job/<int:pk>', views.editJob, name = 'edit-job'),
    path('deleteJob/<int:pk>', views.deleteJob, name = 'deleteJob'),
    path('get-employees/', views.Employees, name = 'Employees'),
    path('employee/add/', views.manage_employee, name='add_employee'),
    path('employee/edit/<int:employee_id>/', views.manage_employee, name='edit_employee'),
    path('assignment/', views.EmployeeAssignmentView.as_view(), name='assignment'),
    path('employee-details/<int:employee_id>/', views.EmployeeDetailsView.as_view(), name='assignment_employee_details'),
    path('update_hours/', views.UpdateHours.as_view(), name='update_hours'),
    path('timesheet-upload/', views.postTimesheet, name ='timesheet-upload'), 
    path('invoice-upload/', views.postInvoiceStaff, name ='invoice-upload'), 
    path('invoice/', views.InvoiceAssignmentView.as_view(), name ='invoice'), 
    path('invoice-details/<int:job_id>/', views.InvoiceView.as_view(), name ='invoice-details'),
    path('create-invoice/', views.saveInvoice.as_view(), name ='create-invoice'),
    path('invoices-list', views.invoice_list, name='invoice-list'),
    path('view-invoice/<int:pk>/', views.view_invoice, name='view-invoice'),
    path('update-invoice/<int:pk>/', views.updateInvoice, name='update-invoice'),
    path('delete-invoice/<int:pk>', views.deleteInvoice, name = 'delete-invoice'),

   
] 

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)