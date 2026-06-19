# DIKA ERP Django Port

Port awal dari `dika-erp` ke Django, dibuat di folder terpisah dari app React lama.

Yang sudah disiapkan:

- struktur project Django
- model domain inti yang mengikuti skema asli
- service untuk booking, attendance, payroll, dan dashboard
- endpoint JSON yang meniru route API lama

## Menjalankan di Windows

```bash
cd C:\Users\tamav\Desktop\PROYEK\erp-padel-yaple-bare
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

## Akun Demo

Setelah `seed_demo`, aplikasi bisa dicoba dengan akun berikut:

- Admin: `admin` / `admin123`
- Staff: `staff` / `staff123`

## Verifikasi

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
```

## Catatan

Port ini sudah punya template Django dasar untuk dashboard, booking, revenue, attendance, payroll, dan sick leave. UI masih bisa dipoles lagi, tapi flow utama sudah bisa dijalankan dari server Django.
