from django import forms

from .models import Attendance, Booking, RevenueRecord, SickLeave

from datetime import date

class AttendanceForm(forms.ModelForm):
    image_proof = forms.ImageField(
        required=True,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})
    )

    class Meta:
        model = Attendance
        fields = ["employee", "work_date", "present", "image_proof"]
        widgets = {
            "employee": forms.Select(attrs={"class": "form-control"}),
            "present": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        current_employee = kwargs.pop('current_employee', None)
        action_type = kwargs.pop('action_type', 'masuk')
        super().__init__(*args, **kwargs)
        
        today_iso = date.today().isoformat()
        self.fields['work_date'].initial = today_iso
        self.fields['work_date'].widget = forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control',
            'value': today_iso,
            'readonly': 'readonly'
        })
        
        # Di Python, .capitalize() berjalan dengan benar
        self.fields['image_proof'].label = f"Foto Bukti Absen {action_type.capitalize()} (Wajib)"
        self.fields['present'].initial = True
        
        if current_employee:
            self.fields['employee'].initial = current_employee
            self.fields['employee'].label_from_instance = lambda obj: f"{obj.full_name}"

        self.fields['employee'].disabled = True
        self.fields['work_date'].disabled = True

class SickLeaveForm(forms.ModelForm):
    # Wajibkan upload bukti surat dokter
    medical_proof = forms.ImageField(
        label="Foto Surat Dokter (Wajib)", 
        required=True,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'})
    )

    class Meta:
        model = SickLeave
        fields = ["employee", "leave_date", "reason", "medical_proof"]
        widgets = {
            "employee": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        current_employee = kwargs.pop('current_employee', None)
        super().__init__(*args, **kwargs)
        
        today_iso = date.today().isoformat()
        
        # 1. SET DATE PICKER MINIMUM HARI INI KE DEPAN
        self.fields['leave_date'].widget = forms.DateInput(attrs={
            'type': 'date', 
            'class': 'form-control',
            'min': today_iso, # Mengunci tanggal masa lalu di browser
            'value': today_iso
        })
        
        # 2. MANDATORY REASON
        self.fields['reason'].required = True
        self.fields['reason'].widget = forms.Textarea(attrs={
            'rows': 4, 
            'class': 'form-control', 
            'placeholder': 'Tulis alasan sakit secara detail...'
        })
        
        # 3. SET INITIAL EMPLOYEE & GREYOUT
        if current_employee:
            self.fields['employee'].initial = current_employee
            self.fields['employee'].label_from_instance = lambda obj: f"{obj.full_name}"

        self.fields['employee'].disabled = True


class RevenueRecordForm(forms.ModelForm):
    class Meta:
        model = RevenueRecord
        fields = ["revenue_date", "sport", "amount", "note"]
        widgets = {
            "revenue_date": forms.DateInput(attrs={"type": "date"}),
            "note": forms.TextInput(attrs={"placeholder": "optional note"}),
        }

class BookingForm(forms.ModelForm):
    booking_date = forms.DateField(
        label="Tanggal Booking",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control', 'id': 'id_booking_date'})
    )
    
    price_per_hour = forms.IntegerField(
        min_value=0, 
        label="Harga per Jam (Rp)", 
        widget=forms.NumberInput(attrs={'placeholder': 'Contoh: 150000', 'class': 'form-control'})
    )
    
    HOURS_CHOICES = [
        (h, f"{h:02d}:00 - {h+1:02d}:00") for h in range(6, 24)
    ]

    selected_hours = forms.MultipleChoiceField(
        choices=HOURS_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'hour-checkbox'}),
        label="Pilih Jam Main"
    )
    
    class Meta:
        model = Booking
        fields = ['booking_date', 'court', 'kind', 'note']
        widgets = {
            'court': forms.Select(attrs={'class': 'form-control', 'id': 'id_court'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            hours = [str(hour) for hour in self.instance.get_hours_list()]
            self.fields['selected_hours'].initial = hours
            if self.instance.duration_hours:
                self.fields['price_per_hour'].initial = int(self.instance.amount / self.instance.duration_hours)

        if 'note' in self.fields:
            self.fields['note'].label = "Nama Customer"
            self.fields['note'].required = True
            self.fields['note'].widget = forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Masukkan nama lengkap customer'
            })
