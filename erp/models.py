from __future__ import annotations

import json
from datetime import time
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import models


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


class Profile(TimeStampedModel):
    ROLE_CHOICES = [
        ("owner", "Owner"),
        ("gm", "GM"),
        ("supervisor", "Supervisor"),
        ("finance", "Finance"),
        ("member_care", "Member Care"),
        ("facility_care", "Facility Care"),
        ("staff", "Staff"),
    ]

    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=32, choices=ROLE_CHOICES, default="member_care")


class Employee(TimeStampedModel):
    DIVISION_CHOICES = [
        ("operations", "Operations"),
        ("finance", "Finance"),
        ("sales", "Sales"),
    ]
    EMP_KIND_CHOICES = [("internal", "Internal"), ("outsource", "Outsource")]
    STATUS_CHOICES = [("active", "Active"), ("inactive", "Inactive")]

    user = models.OneToOneField(User, null=True, blank=True, on_delete=models.SET_NULL)
    full_name = models.CharField(max_length=255)
    division = models.CharField(max_length=32, choices=DIVISION_CHOICES)
    emp_kind = models.CharField(max_length=16, choices=EMP_KIND_CHOICES, default="internal")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="active")
    base_salary = models.IntegerField(default=0)
    daily_rate = models.IntegerField(null=True, blank=True)
    join_date = models.DateField(null=True, blank=True)
    resign_date = models.DateField(null=True, blank=True)


class Court(TimeStampedModel):
    SPORT_CHOICES = [("padel", "Padel"), ("tennis", "Tennis")]
    SUBTYPE_CHOICES = [("indoor", "Indoor"), ("outdoor", "Outdoor")]
    STATUS_CHOICES = [("active", "Active"), ("inactive", "Inactive")]

    name = models.CharField(max_length=255)
    sport = models.CharField(max_length=16, choices=SPORT_CHOICES)
    subtype = models.CharField(max_length=16, choices=SUBTYPE_CHOICES)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="active")
    open_hour = models.PositiveSmallIntegerField(default=6)
    close_hour = models.PositiveSmallIntegerField(default=22)


class PricingRule(models.Model):
    sport = models.CharField(max_length=16)
    subtype = models.CharField(max_length=16, null=True, blank=True)
    label = models.CharField(max_length=64)
    start_hour = models.PositiveSmallIntegerField()
    end_hour = models.PositiveSmallIntegerField()
    hourly_rate = models.IntegerField()
    active = models.BooleanField(default=True)


class Customer(TimeStampedModel):
    code = models.CharField(max_length=32, unique=True)
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=32, blank=True)
    preferred_sport = models.CharField(max_length=16, blank=True)
    is_recurring = models.BooleanField(default=False)


class Membership(TimeStampedModel):
    PAY_STATUS_CHOICES = [("unpaid", "Unpaid"), ("partial", "Partial"), ("paid", "Paid")]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    sport = models.CharField(max_length=16)
    package_name = models.CharField(max_length=255)
    total_sessions = models.PositiveIntegerField()
    rate_per_session = models.IntegerField()
    amount_paid = models.IntegerField(default=0)
    pay_status = models.CharField(max_length=16, choices=PAY_STATUS_CHOICES, default="unpaid")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    sales_pic = models.ForeignKey(Employee, null=True, blank=True, on_delete=models.SET_NULL)
    closing_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

class Booking(TimeStampedModel):
    KIND_CHOICES = [
        ("ayo", "AYO"), 
        ("whatsapp", "WhatsApp"), 
        ("walk_in", "Walk In"), 
        ("member", "Member")
    ]
    STATUS_CHOICES = [("confirmed", "Confirmed"), ("cancelled", "Cancelled"), ("no_show", "No Show")]

    court = models.ForeignKey(Court, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL)
    membership = models.ForeignKey(Membership, null=True, blank=True, on_delete=models.SET_NULL)
    booking_date = models.DateField()
    
    jam_terpilih = models.CharField(max_length=255, default="[]", help_text="Contoh: [6, 7, 8]")
    
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    duration_hours = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    
    kind = models.CharField(max_length=16, choices=KIND_CHOICES, default="walk_in")
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="confirmed")
    amount = models.IntegerField(default=0)
    note = models.TextField(null=True, blank=True) 
    created_by = models.ForeignKey(Profile, null=True, blank=True, on_delete=models.SET_NULL)

    def get_hours_list(self):
        try:
            return json.loads(self.jam_terpilih)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_hours_list(self, hours_list):
        if isinstance(hours_list, list):
            hours_list = [int(h) for h in hours_list]
            hours_list.sort()
            self.jam_terpilih = json.dumps(hours_list)

    def save(self, *args, **kwargs):
        hours = self.get_hours_list()
        
        if hours:
            hours.sort()
            start_hour = hours[0]
            end_hour = hours[-1] + 1
            
            self.start_time = time(start_hour, 0)
            
            if end_hour >= 24:
                self.end_time = time(23, 59, 59)
            else:
                self.end_time = time(end_hour, 0)
                
            self.duration_hours = Decimal(len(hours))
            
        super().save(*args, **kwargs)


class RevenueRecord(TimeStampedModel):
    SPORT_CHOICES = [("tennis", "Tennis"), ("padel", "Padel")]

    revenue_date = models.DateField()
    sport = models.CharField(max_length=16, choices=SPORT_CHOICES)
    amount = models.IntegerField()
    note = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)


class Shift(models.Model):
    SHIFT_TYPE_CHOICES = [("pagi", "Pagi"), ("malam", "Malam"), ("off", "Off")]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    shift_date = models.DateField()
    shift_type = models.CharField(max_length=16, choices=SHIFT_TYPE_CHOICES)
    image_proof = models.ImageField(upload_to="attendance_proofs/", null=True, blank=True)


class Attendance(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    work_date = models.DateField()
    present = models.BooleanField(default=True)
    shift_type = models.CharField(max_length=16, null=True, blank=True)
    source = models.CharField(max_length=16, default="shift")
    image_proof = models.ImageField(upload_to="attendance_proofs/", null=True, blank=True)
    created_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)


class SickLeave(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    leave_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending")
    requested_by = models.ForeignKey(User, related_name="sickleave_requests", on_delete=models.CASCADE)
    approved_by = models.ForeignKey(User, null=True, blank=True, related_name="sickleave_approvals", on_delete=models.SET_NULL)
    approved_at = models.DateTimeField(null=True, blank=True)
    medical_proof = models.ImageField(upload_to="sick_leaves/", null=True, blank=True)


class PayrollRun(models.Model):
    STATUS_CHOICES = [("draft", "Draft"), ("finalized", "Finalized")]

    period_month = models.DateField(unique=True)
    working_days = models.PositiveIntegerField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="draft")
    total_amount = models.IntegerField(default=0)
    finalized_at = models.DateTimeField(null=True, blank=True)
    finalized_by = models.ForeignKey(Profile, null=True, blank=True, on_delete=models.SET_NULL)


class PayrollLine(models.Model):
    payroll_run = models.ForeignKey(PayrollRun, on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    days_worked = models.PositiveIntegerField()
    base_salary = models.IntegerField()
    prorated_amount = models.IntegerField()
    adjustments = models.IntegerField(default=0)
    net_pay = models.IntegerField(default=0)


class Expense(TimeStampedModel):
    expense_date = models.DateField()
    category = models.CharField(max_length=255, blank=True)
    description = models.CharField(max_length=255, blank=True)
    qty = models.PositiveIntegerField(default=1)
    unit_price = models.IntegerField()
    total = models.IntegerField(default=0)
    reimbursed = models.BooleanField(default=False)
