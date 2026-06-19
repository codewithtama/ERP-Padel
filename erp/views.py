from __future__ import annotations

import json
from datetime import date

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .access import admin_required, management_required
from .models import Booking, PayrollLine, PayrollRun
from .services import attendance_from_shifts, create_booking, dashboard_snapshot, generate_payroll_run


def _json_body(request):
    raw = request.body.decode("utf-8") if request.body else "{}"
    return json.loads(raw)


@csrf_exempt
def bookings_endpoint(request):
    if request.method == "GET":
        requested_date = request.GET.get("date") or date.today().isoformat()
        data = list(Booking.objects.filter(booking_date=requested_date).exclude(status="cancelled").values())
        return JsonResponse({"data": data})
    if request.method == "POST":
        try:
            body = _json_body(request)
            booking = create_booking(**body)
            return JsonResponse({"data": {"id": str(booking.id)}}, status=201)
        except ValueError as exc:
            if str(exc) == "COURT_DOUBLE_BOOKED":
                return JsonResponse(
                    {"error": {"code": "COURT_DOUBLE_BOOKED", "message": "Court already booked for that time."}},
                    status=409,
                )
            return JsonResponse({"error": {"code": "CREATE_FAILED", "message": str(exc)}}, status=400)
    return JsonResponse({"error": {"code": "METHOD_NOT_ALLOWED"}}, status=405)


@csrf_exempt
def attendance_from_shifts_endpoint(request):
    if request.method != "POST":
        return JsonResponse({"error": {"code": "METHOD_NOT_ALLOWED"}}, status=405)
    body = _json_body(request)
    result = attendance_from_shifts(date.fromisoformat(body["month"]))
    return JsonResponse({"data": result})


@csrf_exempt
def generate_payroll_endpoint(request):
    if request.method != "POST":
        return JsonResponse({"error": {"code": "METHOD_NOT_ALLOWED"}}, status=405)
    body = _json_body(request)
    run = generate_payroll_run(date.fromisoformat(body["period_month"]), body.get("working_days", 26))
    lines = list(PayrollLine.objects.filter(payroll_run=run).values())
    total = sum(line["net_pay"] for line in lines)
    total_deduction = sum(max(0, line["base_salary"] - line["prorated_amount"]) for line in lines)
    return JsonResponse({"data": {"run_id": str(run.id), "total": total, "totalDeduction": total_deduction, "lines": lines}})


@csrf_exempt
def finalize_payroll_endpoint(request):
    if request.method != "POST":
        return JsonResponse({"error": {"code": "METHOD_NOT_ALLOWED"}}, status=405)
    body = _json_body(request)
    run = PayrollRun.objects.get(id=body["run_id"])
    run.status = "finalized"
    run.save(update_fields=["status"])
    return JsonResponse({"data": {"run_id": str(run.id), "status": run.status}})


def daily_occupancy_endpoint(request):
    requested_date = request.GET.get("date") or date.today().isoformat()
    snapshot = dashboard_snapshot(date.fromisoformat(requested_date))
    return JsonResponse({"data": snapshot})


def dashboard_endpoint(request):
    requested_date = request.GET.get("date") or date.today().isoformat()
    snapshot = dashboard_snapshot(date.fromisoformat(requested_date))
    return JsonResponse({"data": snapshot})

from django.http import JsonResponse

@management_required
def check_booked_hours(request):
    target_date = request.GET.get("date")
    court_id = request.GET.get("court_id")
    
    if not target_date or not court_id:
        return JsonResponse({"booked_hours": []})
        
    bookings = Booking.objects.filter(
        booking_date=target_date,
        court_id=court_id,
        status="confirmed",
        deleted_at__isnull=True
    )
    
    booked_hours = []
    for b in bookings:
        # Langsung gabungkan array jam dari database ke array penampung utama
        booked_hours.extend(b.get_hours_list())
            
    return JsonResponse({"booked_hours": list(set(booked_hours))}) # set() untuk menjamin tidak ada duplikasi angka