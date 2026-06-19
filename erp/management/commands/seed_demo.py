from __future__ import annotations

from datetime import date
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

from erp.models import Booking, Court, Customer, Employee, Expense, PayrollRun, PricingRule, RevenueRecord, Shift, Profile
from erp.services import attendance_from_shifts, generate_payroll_run


class Command(BaseCommand):
    help = "Seed demo data for the DIKA ERP Django port with Array Booking system"

    def handle(self, *args, **options):
        # 1. SEED COURTS
        courts = []
        if not Court.objects.exists():
            for name, sport, subtype in [
                ("Padel 1", "padel", "indoor"),
                ("Padel 2", "padel", "indoor"),
                ("Padel 3", "padel", "outdoor"),
                ("Padel 4", "padel", "outdoor"),
                ("Tennis 1", "tennis", "outdoor"),
                ("Tennis 2", "tennis", "outdoor"),
                ("Tennis 3", "tennis", "indoor"),
            ]:
                courts.append(Court.objects.create(name=name, sport=sport, subtype=subtype))
        else:
            courts = list(Court.objects.all().order_by("name"))

        # 2. SEED PRICING RULES
        if not PricingRule.objects.exists():
            for sport in ["padel", "tennis"]:
                PricingRule.objects.create(sport=sport, subtype=None, label="Off-Peak", start_hour=6, end_hour=17, hourly_rate=200000)
                PricingRule.objects.create(sport=sport, subtype=None, label="Peak", start_hour=17, end_hour=22, hourly_rate=300000)

        # 3. SEED EMPLOYEES
        if not Employee.objects.exists():
            Employee.objects.create(full_name="Ayu Pramesti", division="operations", emp_kind="internal", base_salary=6000000)
            Employee.objects.create(full_name="Bima Santoso", division="finance", emp_kind="internal", base_salary=7500000)
            Employee.objects.create(full_name="Raka Putra", division="sales", emp_kind="outsource", base_salary=0, daily_rate=250000)

        # 4. SEED AUTH GROUPS & USERS (WITH PROFILE SYNC)
        admin_group, _ = Group.objects.get_or_create(name="admin")
        staff_group, _ = Group.objects.get_or_create(name="staff")

        # Setup Admin
        admin_user, _ = User.objects.get_or_create(username="admin", defaults={"is_staff": True, "is_superuser": True, "email": "admin@dika.local"})
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.set_password("admin123")
        admin_user.save()
        admin_user.groups.add(admin_group)

        admin_profile, _ = Profile.objects.update_or_create(
            user=admin_user,
            defaults={"full_name": "Admin Utama", "role": "owner"},
        )

        # Setup Staff
        staff_user, _ = User.objects.get_or_create(username="staff", defaults={"is_staff": False, "is_superuser": False, "email": "staff@dika.local"})
        staff_user.is_staff = False
        staff_user.is_superuser = False
        staff_user.set_password("staff123")
        staff_user.save()
        staff_user.groups.add(staff_group)
        
        Profile.objects.update_or_create(
            user=staff_user,
            defaults={"full_name": "Staff Operasional", "role": "staff"},
        )

        Employee.objects.filter(full_name="Ayu Pramesti").update(user=staff_user)

        # 5. SEED CUSTOMERS
        if not Customer.objects.exists():
            Customer.objects.create(code="CUST-001", full_name="Andi Wijaya", phone="081234567890", preferred_sport="padel")
            Customer.objects.create(code="CUST-002", full_name="Maya Lestari", phone="081298765432", preferred_sport="tennis")

        # 6. SEED BOOKINGS (MENGGUNAKAN FORMAT ARRAY BARU)
        today = date.today()
        if not Booking.objects.exists():
            # Padel 1: Jam 07:00 murni (array: [7])
            b1 = Booking(court=courts[0], booking_date=today, amount=200000, kind="walk_in", created_by=admin_profile)
            b1.set_hours_list([7])
            b1.save()

            # Padel 2: Jam 17:00 murni (array: [17])
            b2 = Booking(court=courts[1], booking_date=today, amount=300000, kind="walk_in", created_by=admin_profile)
            b2.set_hours_list([17])
            b2.save()

            # Tennis 1: Jam 18:00 murni (array: [18])
            b3 = Booking(court=courts[4], booking_date=today, amount=300000, kind="walk_in", created_by=admin_profile)
            b3.set_hours_list([18])
            b3.save()

        # 7. SEED SHIFTS
        if not Shift.objects.exists():
            employees = list(Employee.objects.all())
            for employee in employees:
                Shift.objects.create(employee=employee, shift_date=today.replace(day=1), shift_type="pagi")

        # 8. SEED EXPENSES
        if not Expense.objects.exists():
            Expense.objects.create(
                expense_date=today.replace(day=1),
                category="operational",
                description="Cleaning",
                qty=1,
                unit_price=500000,
                total=500000,
            )

        # 9. SEED REVENUE RECORDS
        if not RevenueRecord.objects.exists():
            demo_rows = [
                (date(2026, 3, 1), "tennis", 207142000),
                (date(2026, 3, 1), "padel", 85296200),
                (date(2026, 4, 1), "tennis", 285075000),
                (date(2026, 4, 1), "padel", 101899268),
                (date(2026, 5, 1), "tennis", 306700000),
                (date(2026, 5, 1), "padel", 132652321),
            ]
            for revenue_date, sport, amount in demo_rows:
                RevenueRecord.objects.create(
                    revenue_date=revenue_date, 
                    sport=sport, 
                    amount=amount, 
                    note="demo seed", 
                    created_by=admin_user
                )

        # 10. GENERATE AUTOMATIONS SERVICES
        attendance_from_shifts(today.replace(day=1))

        if not PayrollRun.objects.filter(period_month=today.replace(day=1)).exists():
            generate_payroll_run(today.replace(day=1), 26)
        else:
            generate_payroll_run(today.replace(day=1), 26)

        self.stdout.write(self.style.SUCCESS("Demo data seeded with correct Array Bookings."))
