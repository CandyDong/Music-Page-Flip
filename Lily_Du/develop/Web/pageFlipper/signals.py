#pageFlipper/signals.py

from django.dispatch import Signal

flip_page_signal = Signal(providing_args=["sheet_music_name", "page_number"])

