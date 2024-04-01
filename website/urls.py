
from django.urls import path
from . import views

urlpatterns = [
    path('',views.home, name='home'),
    #path('login/',views.login_user, name='login'),
    path('logout/',views.logout_user, name='logout'),
    path('roaster/', views.RoasterView.as_view(), name='roaster'),
    path('roaster/booking/<int:pk>', views.viewBooking, name = 'booking'),
    path('edit/<int:pk>', views.editBooking, name = 'editBooking'),
    path('delete/<int:pk>', views.deleteBooking, name = 'deleteBooking'),
    #path('addBooking/', views.createBooking, name = 'addBooking'),
    path('employees/', views.getEmployees, name = 'getEmployees'),
    path('getJobRoles/<int:pk>', views.getJobRoles, name = 'getJobRoles'),

    
   
]