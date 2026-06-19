from django.urls import path

from . import page_views

urlpatterns = [
    path("", page_views.home_page, name="home"),
    path("login/", page_views.login_page, name="login"),
    path("logout/", page_views.logout_page, name="logout"),
    path("bookings/", page_views.bookings_page, name="bookings"),
    path("bookings/cancel/<int:booking_id>/", page_views.cancel_booking_page, name="cancel_booking"),
    path("attendance/", page_views.attendance_page, name="attendance"),
    path("sickleave/", page_views.sickleave_page, name="sickleave"),
    path("payroll/", page_views.payroll_page, name="payroll"),
    path("revenue/", page_views.revenue_page, name="revenue"),
    path("revenue/<int:pk>/delete/", page_views.revenue_delete, name="revenue_delete"),
    path("dashboard/", page_views.dashboard_page, name="dashboard"),
]
