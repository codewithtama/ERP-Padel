from django.urls import path

from . import views

urlpatterns = [
    path("bookings/", views.bookings_endpoint),
    path("bookings/check-hours/", views.check_booked_hours),
    path("attendance/from-shifts/", views.attendance_from_shifts_endpoint),
    path("payroll/runs/generate/", views.generate_payroll_endpoint),
    path("payroll/runs/finalize/", views.finalize_payroll_endpoint),
    path("occupancy/daily/", views.daily_occupancy_endpoint),
    path("dashboard/", views.dashboard_endpoint),
]
