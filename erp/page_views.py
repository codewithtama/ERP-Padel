from __future__ import annotations

from datetime import date

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .access import admin_required, is_admin_user, management_required, redirect_home_for_user, staff_required
from .forms import AttendanceForm, BookingForm, RevenueRecordForm, SickLeaveForm
from .models import Attendance, Booking, Court, Employee, PayrollLine, PayrollRun, Profile, RevenueRecord, SickLeave
from .services import dashboard_snapshot

def _today() -> date:
    return date.today()


def _month_start(value: date | None = None) -> date:
    current = value or _today()
    return current.replace(day=1)


def _employee_for_user(user):
    return Employee.objects.filter(user=user).first()


def _profile_for_user(user):
    try:
        return user.profile
    except ObjectDoesNotExist:
        pass
    return Profile.objects.filter(user=user).first()


def login_page(request):
    if request.user.is_authenticated:
        return redirect_home_for_user(request.user)
    error = None
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is None:
            error = "Username atau password salah."
        elif not user.is_active:
            error = "Akun nonaktif."
        else:
            login(request, user)
            return redirect_home_for_user(user)
    return render(request, "login.html", {"error": error, "logged_out": request.GET.get("logged_out")})


def logout_page(request):
    logout(request)
    
    # redirect ke halaman login. 
    # Jika ingin membawa parameter "logged_out", kita bisa pasang lewat query param
    return redirect(f"{reverse('login')}?logged_out=true")


@admin_required
def dashboard_page(request):
    current = _today()
    snapshot = dashboard_snapshot(current)
    return render(request, "dashboard.html", {"snapshot": snapshot, "today": current})


@management_required
def bookings_page(request):
    current = request.GET.get("date") or _today().isoformat()
    selected_date = date.fromisoformat(current)
    user_is_admin = is_admin_user(request.user)
    
    # ========================================================
    # LOGIKA UPDATE / EDIT (Mendeteksi ID Instance)
    # ========================================================
    edit_id = request.GET.get("edit_id")
    booking_instance = None
    if edit_id:
        booking_instance = get_object_or_404(Booking, id=edit_id, deleted_at__isnull=True)
    
    form = BookingForm(
        request.POST or None,
        instance=booking_instance,
        initial={"booking_date": selected_date},
    )
    
    if request.method == "POST" and form.is_valid():
        target_date = form.cleaned_data['booking_date'] 
        court = form.cleaned_data['court']
        kind = form.cleaned_data['kind']
        price_per_hour = form.cleaned_data['price_per_hour']
        
        selected_hours = [int(h) for h in form.cleaned_data['selected_hours']]
        selected_hours.sort()
        
        # JIKA GAGAL: Kembalikan dan langsung lempar fokus layar ke area form (#booking-form-section)
        if not selected_hours:
            messages.error(request, "Gagal! Anda belum memilih jam main.")
            return redirect(f"/bookings/?date={target_date.isoformat()}#booking-form-section")

        existing_bookings = Booking.objects.filter(
            booking_date=target_date, court=court, status="confirmed", deleted_at__isnull=True
        )
        if booking_instance:
            existing_bookings = existing_bookings.exclude(id=booking_instance.id)
            
        collision = False
        for b in existing_bookings:
            booked_list = b.get_hours_list() 
            for hour in selected_hours:
                if hour in booked_list:
                    collision = True
                    break
            if collision: break
        
        if collision:
            messages.error(request, "Gagal! Lapangan sudah ter-booking pada jam tersebut.")
            return redirect(f"/bookings/?date={target_date.isoformat()}#booking-form-section")
        
        # JIKA LOLOS VALIDASI BENTROKAN:
        else:
            with transaction.atomic():
                total_hours = len(selected_hours)
                total_amount = total_hours * price_per_hour
                customer_name = form.cleaned_data['note']
                jam_str = ", ".join([f"{h:02d}:00" for h in selected_hours])
                
                booking = form.save(commit=False)
                booking.booking_date = target_date 
                booking.amount = total_amount
                booking.set_hours_list(selected_hours)
                
                if not booking_instance:
                    booking.created_by = _profile_for_user(request.user)
                
                booking.note = customer_name
                booking.save()
                
                # MAPPING PEMBUATAN / UPDATE REVENUE RECORD MANUAL
                sport_type = 'tennis' if 'tennis' in court.name.lower() else 'padel'
                if booking_instance:
                    # Update data revenue lama berdasarkan kecocokan nama customer lama
                    RevenueRecord.objects.filter(
                        revenue_date=target_date, 
                        note__contains=f"Cust: {booking_instance.note}"
                    ).update(
                        amount=total_amount,
                        note=f"{court.name} [{kind.upper()}] (Jam: {jam_str}) - Cust: {customer_name}"
                    )
                else:
                    # Buat record baru jika pesanan gres baru masuk
                    RevenueRecord.objects.create(
                        revenue_date=target_date,
                        sport=sport_type,
                        amount=total_amount,
                        note=f"{court.name} [{kind.upper()}] (Jam: {jam_str}) - Cust: {customer_name}",
                        created_by=request.user
                    )
                
                msg = f"Booking {customer_name} berhasil diperbarui." if booking_instance else "Booking sukses disimpan."
                messages.success(request, msg)
                return redirect(f"/bookings/?date={target_date.isoformat()}")
            
    # ========================================================
    # LOGIKA READ (RANGKAI GRID)
    # ========================================================
    courts = list(Court.objects.filter(status="active", deleted_at__isnull=True).order_by("name"))
    bookings = list(Booking.objects.filter(booking_date=selected_date, status="confirmed", deleted_at__isnull=True))
    
    hours = list(range(6, 24))
    rows = []
    for hour in hours:
        cells = []
        for court in courts:
            matched_booking = None
            for b in bookings:
                if b.court_id == court.id and hour in b.get_hours_list():
                    matched_booking = b
                    break
            cells.append({"booking": matched_booking})
        rows.append({"hour": hour, "cells": cells})
        
    return render(
        request, "bookings.html",
        {
            "courts": courts, "bookings": bookings, "selected_date": selected_date, 
            "hours": hours, "rows": rows, "form": form, "user_is_admin": user_is_admin,
            "booking_instance": booking_instance,
        },
    )

# =================================================================
# ACTION VIEW: HALAMAN POP-UP KONFIRMASI DELETE MANUAL (KHUSUS ADMIN)
# =================================================================
@admin_required
def cancel_booking_page(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    
    if request.method == "POST":
        with transaction.atomic():
            # 1. Soft delete data booking utama
            booking.status = "cancelled"
            booking.save()
            
            # 2. MANUAL CASCADE CLEANUP: Cari dan lenyapkan RevenueRecord yang sinkron dengan data ini
            RevenueRecord.objects.filter(
                revenue_date=booking.booking_date,
                note__contains=f"Cust: {booking.note}"
            ).delete()
            
        messages.success(request, f"Booking atas nama {booking.note} sukses dibatalkan!")
        return redirect(f"/bookings/?date={booking.booking_date.isoformat()}")
        
    return render(request, "booking_confirm_cancel.html", {"booking": booking})

@staff_required
def attendance_page(request):
    current_employee = _employee_for_user(request.user)
    
    today = date.today()
    action_type = "masuk"
    already_all_done = False
    no_employee = current_employee is None

    if current_employee:
        has_in = Attendance.objects.filter(employee=current_employee, work_date=today, source="masuk").exists()
        has_out = Attendance.objects.filter(employee=current_employee, work_date=today, source="keluar").exists()
        if has_in and has_out:
            already_all_done = True
        elif has_in:
            action_type = "keluar"

    form = AttendanceForm(
        request.POST or None,
        request.FILES or None,
        current_employee=current_employee,
        action_type=action_type,
    )

    if request.method == "POST" and not already_all_done and not no_employee:
        if form.is_valid():
            attendance = form.save(commit=False)
            attendance.employee = current_employee
            attendance.work_date = today
            attendance.created_by = request.user
            attendance.present = True
            attendance.source = action_type
            attendance.save()
            messages.success(request, f"Absensi {action_type} berhasil disimpan.")
            return redirect("attendance")

    # --- HITUNG DATA RINGKASAN BULANAN ---
    month = request.GET.get("month") or _month_start().isoformat()
    month_date = date.fromisoformat(month)
    rows = []
    employees = Employee.objects.filter(status="active", deleted_at__isnull=True).order_by("full_name")
    
    for employee in employees:
        # PERBAIKAN: Hitung work_date yang unik (distinct) agar absen masuk & keluar tidak dihitung 2 hari
        days_worked = (
            Attendance.objects.filter(
                employee=employee,
                work_date__year=month_date.year,
                work_date__month=month_date.month,
                present=True,
            )
            .aggregate(days=Count("work_date", distinct=True))["days"] or 0
        )
        rows.append({
            "employee": employee,
            "days_worked": days_worked,
        })
    return render(
        request,
        "attendance.html",
        {
            "rows": rows, 
            "month": month_date, 
            "form": form, 
            "action_type": action_type,
            "already_all_done": already_all_done,
            "current_employee": current_employee,
            "no_employee": no_employee,
        },
    )

@staff_required
def sickleave_page(request):
    current_employee = _employee_for_user(request.user)
    no_employee = current_employee is None
    
    form = SickLeaveForm(request.POST or None, request.FILES or None, current_employee=current_employee)
    
    if request.method == "POST" and form.is_valid() and not no_employee:
        leave = form.save(commit=False)
        leave.requested_by = request.user
        leave.employee = current_employee
        leave.status = "pending"
        leave.save()
        messages.success(request, "Pengajuan sick leave terkirim dan menunggu approval admin.")
        return redirect("sickleave")

    sick_leaves = list(
        SickLeave.objects.filter(requested_by=request.user)
        .select_related("employee", "approved_by")
        .order_by("-leave_date")
    )
    return render(request, "sickleave.html", {"form": form, "sick_leaves": sick_leaves, "no_employee": no_employee})


@admin_required
def payroll_page(request):
    month = request.GET.get("month") or _month_start().isoformat()
    month_date = date.fromisoformat(month)
    run = PayrollRun.objects.filter(period_month=month_date.replace(day=1)).first()
    raw_lines = list(PayrollLine.objects.filter(payroll_run=run).select_related("employee")) if run else []
    lines = []
    total_deduction = 0
    for line in raw_lines:
        deduction = max(0, line.base_salary - line.prorated_amount)
        total_deduction += deduction
        lines.append({"line": line, "deduction": deduction})
    return render(
        request,
        "payroll.html",
        {
            "month": month_date,
            "run": run,
            "lines": lines,
            "total_deduction": total_deduction,
        },
    )


@admin_required
def revenue_page(request):
    # 1. AMBIL PARAMETER TANGGAL SEPERTI DI PAGE BOOKINGS
    # Jika tidak ada parameter ?date= di URL, gunakan tanggal hari ini
    date_param = request.GET.get("date")
    if date_param:
        try:
            # Jika formatnya YYYY-MM (dari input type="month")
            if len(date_param) == 7: 
                selected_date = date.fromisoformat(f"{date_param}-01") # Tempelkan tanggal 01 secara artifisial
            else:
                selected_date = date.fromisoformat(date_param)
        except ValueError:
            selected_date = date.today()
    else:
        selected_date = date.today()

    # Tentukan awal bulan dan akhir bulan berjalan untuk filter query
    start_of_month = selected_date.replace(day=1)
    # Trik mencari hari terakhir: lompati ke bulan depan hari ke-1, lalu kurangi 1 hari
    if selected_date.month == 12:
        end_of_month = selected_date.replace(year=selected_date.year + 1, month=1, day=1)
    else:
        end_of_month = selected_date.replace(month=selected_date.month + 1, day=1)

    # 2. PROSES UPDATE / DELETE INSTANCE FORM
    edit_id = request.GET.get("edit")
    instance = RevenueRecord.objects.filter(id=edit_id).first() if edit_id else None
    form = RevenueRecordForm(request.POST or None, instance=instance)

    if request.method == "POST" and form.is_valid():
        record = form.save(commit=False)
        record.created_by = request.user
        record.save()
        messages.success(request, "Revenue record saved.")
        return redirect(f"/revenue/?date={selected_date.isoformat()}")

    if request.method == "POST" and request.POST.get("delete_id"):
        RevenueRecord.objects.filter(id=request.POST["delete_id"]).delete()
        messages.success(request, "Revenue record deleted.")
        return redirect(f"/revenue/?date={selected_date.isoformat()}")

    # ========================================================
    # 3. FILTER DATA RECORDS HANYA DI BULAN BERJALAN INI SAJA
    # ========================================================
    records = (
        RevenueRecord.objects.filter(
            revenue_date__gte=start_of_month,
            revenue_date__lt=end_of_month
        )
        .select_related("created_by")
        .order_by("-revenue_date", "-id")
    )

    # ========================================================
    # 4. KALKULASI TOTAL KARTU ATAS (HANYA BULAN BERJALAN INI)
    # ========================================================
    current_month_totals = RevenueRecord.objects.filter(
        revenue_date__gte=start_of_month,
        revenue_date__lt=end_of_month
    ).aggregate(
        tennis=Sum("amount", filter=Q(sport="tennis")),
        padel=Sum("amount", filter=Q(sport="padel")),
        total=Sum("amount")
    )

    total_tennis = current_month_totals["tennis"] or 0
    total_padel = current_month_totals["padel"] or 0
    total_all = current_month_totals["total"] or 0

    # ========================================================
    # 5. QUICK SUMMARY TABEL KANAN (TETAP SEMUA BULAN AGAR PRESTASI TERLIHAT)
    # ========================================================
    summary_rows = (
        RevenueRecord.objects.annotate(period=TruncMonth("revenue_date"))
        .values("period")
        .annotate(
            tennis=Sum("amount", filter=Q(sport="tennis")),
            padel=Sum("amount", filter=Q(sport="padel")),
            total=Sum("amount"),
        )
        .order_by("period")
    )
    
    grand_tennis = 0
    grand_padel = 0
    grand_total = 0
    summary = []
    for row in summary_rows:
        tennis = row["tennis"] or 0
        padel = row["padel"] or 0
        total = row["total"] or 0
        summary.append({"period": row["period"], "tennis": tennis, "padel": padel, "total": total})
        grand_tennis += tennis
        grand_padel += padel
        grand_total += total

    return render(
        request,
        "revenue.html",
        {
            "form": form,
            "records": records,
            "summary": summary,
            "total_tennis": total_tennis,
            "total_padel": total_padel,
            "total_all": total_all,
            "grand_tennis": grand_tennis,
            "grand_padel": grand_padel,
            "grand_total": grand_total,
            "editing": instance,
            "selected_date": selected_date,
        },
    )


@admin_required
def revenue_delete(request, pk: int):
    if request.method == "POST":
        RevenueRecord.objects.filter(id=pk).delete()
        messages.success(request, "Revenue record deleted.")
    return redirect("revenue")


def home_page(request):
    if not request.user.is_authenticated:
        # Menggunakan redirect ke nama URL 'login'
        return redirect("login")
    return redirect_home_for_user(request.user)


def forbidden_page(request):
    return redirect("login")
