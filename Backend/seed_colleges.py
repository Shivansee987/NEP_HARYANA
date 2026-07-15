import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from apps.authentication.models import College

colleges = [
    ("Government College Hisar", "C-10001"),
    ("Government College Ambala", "C-10002"),
    ("Government College Karnal", "C-10003"),
    ("Government College Rohtak", "C-10004"),
    ("Government College Sonipat", "C-10005"),
    ("Government College Panipat", "C-10006"),
    ("Government College Kurukshetra", "C-10007"),
    ("Government College Gurugram", "C-10008"),
    ("Government College Faridabad", "C-10009"),
    ("Government College Jhajjar", "C-10010"),
    ("Government College Sirsa", "C-10011"),
    ("Government College Bhiwani", "C-10012"),
    ("Government College Rewari", "C-10013"),
    ("Government College Kaithal", "C-10014"),
    ("Government College Jind", "C-10015"),
]

created = 0

for name, aishe in colleges:
    _, is_created = College.objects.get_or_create(
        aishe_code=aishe,
        defaults={"name": name}
    )
    if is_created:
        created += 1

