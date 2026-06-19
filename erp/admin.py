from django.contrib import admin
from django.utils import timezone

from .models import Attendance, Booking, Court, Customer, Employee, Expense, Membership, PayrollLine, PayrollRun, PricingRule, Profile, RevenueRecord, Shift, SickLeave


@admin.register(SickLeave)
class SickLeaveAdmin(admin.ModelAdmin):
    list_display = ("employee", "leave_date", "status", "requested_by", "approved_by", "approved_at")
    list_filter = ("status", "leave_date")
    search_fields = ("employee__full_name", "reason", "requested_by__username")
    actions = ("approve_selected",)

    @admin.action(description="Approve selected sick leave requests")
    def approve_selected(self, request, queryset):
        queryset.filter(status="pending").update(status="approved", approved_by_id=request.user.id, approved_at=timezone.now())

admin.site.register(Profile)
admin.site.register(Employee)
admin.site.register(Court)
admin.site.register(PricingRule)
admin.site.register(Customer)
admin.site.register(Membership)
admin.site.register(Booking)
admin.site.register(RevenueRecord)
admin.site.register(Shift)
admin.site.register(Attendance)
admin.site.register(PayrollRun)
admin.site.register(PayrollLine)
admin.site.register(Expense)
