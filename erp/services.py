from __future__ import annotations

from datetime import date, timedelta

from django.db import transaction
from django.db.models import Count, Q, Sum

from .models import Attendance, Booking, Court, Employee, Expense, PayrollLine, PayrollRun, PricingRule, Shift


def _month_bounds(month: date) -> tuple[date, date]:
    start = month.replace(day=1)
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    return start, end


def resolve_booking_price(court: Court, start_time, end_time) -> int:
    total = 0
    hour = start_time.hour
    while hour < end_time.hour:
        rule = (
            PricingRule.objects.filter(
                sport=court.sport,
                active=True,
                start_hour__lte=hour,
                end_hour__gt=hour,
            )
            .filter(Q(subtype__isnull=True) | Q(subtype=court.subtype))
            .order_by("-subtype")
            .first()
        )
        total += rule.hourly_rate if rule else 0
        hour += 1
    return total


def create_booking(*, court_id, booking_date, start_time, end_time, customer_id=None, membership_id=None, kind="walk_in"):
    court = Court.objects.get(id=court_id)
    price = resolve_booking_price(court, start_time, end_time)
    overlapping = Booking.objects.filter(
        court_id=court_id,
        booking_date=booking_date,
        status="confirmed",
        deleted_at__isnull=True,
    ).exclude(end_time__lte=start_time).exclude(start_time__gte=end_time)
    if overlapping.exists():
        raise ValueError("COURT_DOUBLE_BOOKED")
    return Booking.objects.create(
        court_id=court_id,
        booking_date=booking_date,
        start_time=start_time,
        end_time=end_time,
        customer_id=customer_id,
        membership_id=membership_id,
        kind=kind,
        amount=price,
    )


def attendance_from_shifts(month: date) -> dict[str, int]:
    start, end = _month_bounds(month)
    created = 0
    updated = 0
    for shift in Shift.objects.filter(shift_date__gte=start, shift_date__lt=end):
        present = shift.shift_type != "off"
        _, is_created = Attendance.objects.update_or_create(
            employee=shift.employee,
            work_date=shift.shift_date,
            defaults={"present": present, "shift_type": shift.shift_type, "source": "shift"},
        )
        created += int(is_created)
        updated += int(not is_created)
    return {"created": created, "updated": updated}


@transaction.atomic
def generate_payroll_run(period_month: date, working_days: int) -> PayrollRun:
    period_month = period_month.replace(day=1)
    run, _ = PayrollRun.objects.update_or_create(
        period_month=period_month,
        defaults={"working_days": working_days, "status": "draft", "total_amount": 0},
    )
    PayrollLine.objects.filter(payroll_run=run).delete()
    start, end = _month_bounds(period_month)
    attendance_counts = (
        Attendance.objects.filter(work_date__gte=start, work_date__lt=end, present=True)
        .values("employee_id")
        .annotate(days=Count("id"))
    )
    by_employee = {row["employee_id"]: row["days"] for row in attendance_counts}

    total_amount = 0
    for employee in Employee.objects.filter(status="active", deleted_at__isnull=True):
        days_worked = by_employee.get(employee.id, 0)
        if employee.emp_kind == "outsource":
            prorated_amount = (employee.daily_rate or 0) * days_worked
        else:
            if working_days > 0:
                prorated_amount = employee.base_salary - round(
                    (working_days - days_worked) * (employee.base_salary / working_days)
                )
            else:
                prorated_amount = employee.base_salary
        PayrollLine.objects.create(
            payroll_run=run,
            employee=employee,
            days_worked=days_worked,
            base_salary=employee.base_salary,
            prorated_amount=prorated_amount,
            adjustments=0,
            net_pay=prorated_amount,
        )
        total_amount += prorated_amount

    run.total_amount = total_amount
    run.save(update_fields=["total_amount"])
    return run


def dashboard_snapshot(day: date) -> dict:
    active_bookings = Booking.objects.filter(
        booking_date=day,
        status__in=["confirmed"],
        deleted_at__isnull=True,
    )
    courts = (
        active_bookings.values("court_id", "court__name", "court__sport")
        .annotate(booked_hours=Sum("duration_hours"))
        .order_by("court__name")
    )
    booked_hours = sum(float(row["booked_hours"] or 0) for row in courts)
    capacity = 112
    overall_occ = round((booked_hours / capacity) * 100, 1) if capacity else 0
    padel_hours = sum(float(row["booked_hours"] or 0) for row in courts if row["court__sport"] == "padel")
    tennis_hours = sum(float(row["booked_hours"] or 0) for row in courts if row["court__sport"] == "tennis")

    period_start = day.replace(day=1)
    revenue = (
        Booking.objects.filter(booking_date__gte=period_start, booking_date__lte=day, status="confirmed", deleted_at__isnull=True)
        .aggregate(total=Sum("amount"))["total"]
        or 0
    )
    payroll = (
        PayrollRun.objects.filter(period_month=period_start)
        .aggregate(total=Sum("total_amount"))["total"]
        or 0
    )
    expenses = (
        Expense.objects.filter(expense_date__gte=period_start, expense_date__lte=day, deleted_at__isnull=True)
        .aggregate(total=Sum("total"))[
            "total"
        ]
        or 0
    )
    return {
        "courts": list(courts),
        "overallOcc": overall_occ,
        "padelOcc": round((padel_hours / 64) * 100, 1) if 64 else 0,
        "tennisOcc": round((tennis_hours / 48) * 100, 1) if 48 else 0,
        "revenue": revenue,
        "netPosition": revenue - payroll - expenses,
        "payroll": payroll,
    }
