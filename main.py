import os
import sys
import random
import secrets
from decimal import Decimal
import certifi

from kivy.app import App
from kivy.utils import platform


def secure_clear_string(s: str) -> None:
    """
    Attempt to overwrite a string's contents in memory.
    Note: Python strings are immutable, so this is best-effort.
    The string object itself should be dereferenced after calling this.
    """
    if not s:
        return
    try:
        import ctypes
        # Get the address of the string's buffer
        # This is CPython-specific and may not work on all platforms
        str_len = len(s)
        if str_len > 0:
            # Overwrite with random data
            ptr = ctypes.cast(id(s), ctypes.POINTER(ctypes.c_char))
            # String data starts after the PyObject header (platform-dependent)
            # This is a best-effort approach
            offset = sys.getsizeof('')
            for i in range(str_len):
                try:
                    ptr[offset + i] = b'\x00'
                except Exception:
                    break
    except Exception:
        pass  # Best effort - some platforms won't support this


def secure_clear_bytearray(ba: bytearray) -> None:
    """Securely zero out a bytearray."""
    if ba:
        for i in range(len(ba)):
            ba[i] = 0


def set_secure_file_permissions(file_path: str) -> None:
    """
    Set secure file permissions (owner read/write only) on wallet files.
    This prevents other users/apps from reading sensitive wallet data.
    On Android, this is less critical as app sandboxing provides isolation,
    but it's still good practice.
    """
    if not file_path or not os.path.exists(file_path):
        return
    try:
        # Set file permissions to 0o600 (owner read/write only)
        # This is equivalent to -rw------- on Unix systems
        os.chmod(file_path, 0o600)
    except Exception:
        pass  # Best effort - some platforms may not support chmod


def set_secure_dir_permissions(dir_path: str) -> None:
    """
    Set secure directory permissions (owner read/write/execute only).
    """
    if not dir_path or not os.path.exists(dir_path):
        return
    try:
        # Set directory permissions to 0o700 (owner read/write/execute only)
        os.chmod(dir_path, 0o700)
    except Exception:
        pass  # Best effort


# Track scheduled clipboard clear events so we can cancel them if needed
_clipboard_clear_event = None


def clipboard_copy_with_timeout(text: str, timeout_seconds: int = 60) -> None:
    """
    Copy text to clipboard and automatically clear it after a timeout.
    This prevents sensitive data (addresses, seeds, TXIDs) from remaining
    in clipboard indefinitely where other apps could access it.
    
    Args:
        text: The text to copy to clipboard
        timeout_seconds: How long before clipboard is cleared (default 60 seconds)
    """
    global _clipboard_clear_event
    from kivy.core.clipboard import Clipboard
    from kivy.clock import Clock
    
    # Cancel any pending clipboard clear
    if _clipboard_clear_event is not None:
        try:
            _clipboard_clear_event.cancel()
        except Exception:
            pass
    
    # Copy to clipboard
    try:
        Clipboard.copy(text)
    except Exception:
        return
    
    # Schedule clipboard clear
    def clear_clipboard(dt):
        global _clipboard_clear_event
        try:
            # Only clear if clipboard still contains our text
            current = Clipboard.paste()
            if current == text:
                Clipboard.copy("")
        except Exception:
            pass
        _clipboard_clear_event = None
    
    _clipboard_clear_event = Clock.schedule_once(clear_clipboard, timeout_seconds)


def get_persistent_data_dir():
    """
    Get a persistent data directory that survives app updates on Android.
    On Android, Kivy's user_data_dir can be unreliable and may get cleared.
    This function uses android.storage.app_storage_path() which is more reliable.
    """
    if platform == 'android':
        try:
            from android.storage import app_storage_path
            path = app_storage_path()
            return path
        except ImportError:
            # Fallback if android.storage is not available
            try:
                from jnius import autoclass
                Context = autoclass('android.content.Context')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                activity = PythonActivity.mActivity
                files_dir = activity.getFilesDir().getAbsolutePath()
                return files_dir
            except Exception:
                return None
    return None
from kivy.lang import Builder
from kivy.properties import (
    StringProperty,
    ListProperty,
    BooleanProperty,
    NumericProperty,
)
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.modalview import ModalView
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.widget import Widget
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.core.clipboard import Clipboard
from kivy.metrics import dp

# Keep IME under the focused field, per the referenced workaround
Window.softinput_mode = "below_target"
import threading
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import ObjectProperty
from datetime import datetime
from typing import cast
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.factory import Factory
from typing import Optional


# Electrum / Frencoin imports
from electrum.simple_config import SimpleConfig
from electrum.network import Network
from electrum.wallet import Wallet, WalletDB, WalletStorage, create_new_wallet
from electrum.transaction import PartialTxOutput
from electrum.bitcoin import COIN, is_address
from electrum.util import (
    NotEnoughFunds,
    WalletFileException,
    create_and_start_event_loop,
)
from electrum import constants

# Network configuration loaded


def format_seed_3col(seed: str, words_per_row: int = 3) -> str:
    """
    Format a seed into perfectly aligned columns with horizontal ordering.
    For 12 words with 3 columns:
       1. word1      2. word2      3. word3
       4. word4      5. word5      6. word6
       7. word7      8. word8      9. word9
      10. word10    11. word11    12. word12
    """
    words = (seed or "").split()
    if not words:
        return ""

    n = len(words)
    num_rows = (n + words_per_row - 1) // words_per_row

    # Find the max word length in each column for alignment
    # Using horizontal ordering: word_idx = row * words_per_row + col
    col_widths = []
    for col_idx in range(words_per_row):
        max_len = 0
        for row_idx in range(num_rows):
            word_idx = row_idx * words_per_row + col_idx
            if word_idx < n:
                max_len = max(max_len, len(words[word_idx]))
        col_widths.append(max_len)

    lines = []
    for row_idx in range(num_rows):
        row_parts = []
        for col_idx in range(words_per_row):
            word_idx = row_idx * words_per_row + col_idx
            if word_idx < n:
                word_num = word_idx + 1
                word = words[word_idx]
                # Fixed width: "XX. word" with word padded to column width
                entry = f"{word_num:>2}. {word:<{col_widths[col_idx]}}"
                row_parts.append(entry)
        lines.append("   ".join(row_parts))

    return "\n".join(lines)


def format_masked_seed(
    seed: str, missing_indices, words_per_row: int = 4, blank_placeholder: str = "____"
) -> str:
    """
    Format seed with perfectly aligned columns using horizontal ordering,
    blanking out words at indices in `missing_indices`.
    """
    words = (seed or "").split()
    if not words:
        return ""

    missing = set(missing_indices or [])
    n = len(words)
    num_rows = (n + words_per_row - 1) // words_per_row

    # Find the max word length in each column for alignment
    # Using horizontal ordering: word_idx = row * words_per_row + col
    col_widths = []
    for col_idx in range(words_per_row):
        max_len = 0
        for row_idx in range(num_rows):
            word_idx = row_idx * words_per_row + col_idx
            if word_idx < n:
                show_word = (
                    blank_placeholder if word_idx in missing else words[word_idx]
                )
                max_len = max(max_len, len(show_word))
        col_widths.append(max_len)

    lines = []
    for row_idx in range(num_rows):
        row_parts = []
        for col_idx in range(words_per_row):
            word_idx = row_idx * words_per_row + col_idx
            if word_idx < n:
                word_num = word_idx + 1
                show_word = (
                    blank_placeholder if word_idx in missing else words[word_idx]
                )
                # Fixed width: "XX. word" with word padded to column width
                entry = f"{word_num:>2}. {show_word:<{col_widths[col_idx]}}"
                row_parts.append(entry)
        lines.append("   ".join(row_parts))

    return "\n".join(lines)


def format_amount_7chars(value: Decimal) -> str:
    """
    Format an amount to fit in 7 characters max (including minus sign and decimal point).
    Uses scientific notation for large values.
    Removes trailing zeros after decimal point.
    """
    try:
        f_val = float(value)
        abs_val = abs(f_val)
        is_negative = f_val < 0
        # Reserve 1 char for minus sign if negative
        max_chars = 6 if is_negative else 7

        if abs_val >= 1_000_000:
            # Use scientific notation with exponent
            # e.g., "1.234e6" (7 chars), "-1.23e6" (7 chars), "1.2e10" (6 chars)
            import math

            exp = int(math.floor(math.log10(abs_val)))
            mantissa = abs_val / (10**exp)
            # Available chars: 7 total, minus sign (0-1), digit (1), 'e' (1), exp digits
            sign_chars = 1 if is_negative else 0
            exp_chars = len(str(exp))
            # Calculate remaining space for decimal portion (dot + digits)
            # 7 - sign - mantissa_digit - 'e' - exp_digits
            remaining = 7 - sign_chars - 1 - 1 - exp_chars
            if remaining >= 2:
                # Room for decimal point and at least one digit
                decimal_places = remaining - 1  # -1 for the decimal point
                # Check if rounding will push mantissa to 10
                rounded_mantissa = round(mantissa, decimal_places)
                if rounded_mantissa >= 10:
                    exp += 1
                    mantissa = mantissa / 10
                    # Recalculate with new exponent
                    exp_chars = len(str(exp))
                    remaining = 7 - sign_chars - 1 - 1 - exp_chars
                    decimal_places = max(0, remaining - 1)
                if is_negative:
                    return f"-{mantissa:.{decimal_places}f}e{exp}"
                else:
                    return f"{mantissa:.{decimal_places}f}e{exp}"
            else:
                # No room for decimal, just show whole mantissa
                rounded = int(round(mantissa))
                if rounded >= 10:
                    exp += 1
                    rounded = 1
                if is_negative:
                    return f"-{rounded}e{exp}"
                else:
                    return f"{rounded}e{exp}"
        elif abs_val >= 10_000:
            # 5 digits before decimal, need max_chars - 5 for decimal places
            decimal_places = max(0, max_chars - 6)  # -6 for "XXXXX."
            formatted = f"{f_val:.{decimal_places}f}"
        elif abs_val >= 1_000:
            decimal_places = max(0, max_chars - 5)  # -5 for "XXXX."
            formatted = f"{f_val:.{decimal_places}f}"
        elif abs_val >= 100:
            decimal_places = max(0, max_chars - 4)  # -4 for "XXX."
            formatted = f"{f_val:.{decimal_places}f}"
        elif abs_val >= 10:
            decimal_places = max(0, max_chars - 3)  # -3 for "XX."
            formatted = f"{f_val:.{decimal_places}f}"
        elif abs_val >= 1:
            decimal_places = max(0, max_chars - 2)  # -2 for "X."
            formatted = f"{f_val:.{decimal_places}f}"
        else:
            # Values < 1, e.g., 0.123456
            decimal_places = max(0, max_chars - 2)  # -2 for "0."
            formatted = f"{f_val:.{decimal_places}f}"

        # Remove trailing zeros after decimal, but keep at least one decimal place for clarity
        if "." in formatted:
            formatted = formatted.rstrip("0").rstrip(".")
        return formatted
    except Exception:
        return str(value)[:7]


# Keep old name as alias for compatibility
def format_amount_6chars(value: Decimal) -> str:
    return format_amount_7chars(value)


# -------------------------------------------------------
# Start Electrum's asyncio loop once, in its own thread
# -------------------------------------------------------
_ELECTRUM_LOOP, _ELECTRUM_STOPPING_FUT, _ELECTRUM_LOOP_THREAD = (
    create_and_start_event_loop()
)

KV = """
<MainScreen>:
    orientation: 'vertical'
    padding: '10dp'
    spacing: '10dp'

    # Header with logo + title + menu
    BoxLayout:
        orientation: 'horizontal'
        size_hint_y: None
        height: '110dp'
        spacing: '10dp'
        Image:
            source: 'assets/icon.png'
            size_hint_x: None
            width: '110dp'
            allow_stretch: True
            keep_ratio: True
        BoxLayout:
            orientation: 'vertical'
            Label:
                text: 'FRENDROID WALLET'
                font_size: '26sp'
                bold: True
                halign: 'left'
                valign: 'middle'
                text_size: self.size
            BoxLayout:
                orientation: 'horizontal'
                size_hint_y: None
                height: '32dp'
                spacing: '10dp'
                Button:
                    text: 'Menu'
                    size_hint_x: None
                    width: '120dp'
                    on_release: app.open_main_menu()
                Widget:

    # RECEIVE
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: None
        height: self.minimum_height
        Label:
            text: 'Frencoin Address:'
            size_hint_y: None
            height: self.texture_size[1]
            halign: 'left'
            valign: 'middle'
        BoxLayout:
            size_hint_y: None
            height: '40dp'
            spacing: '8dp'
            AddressBox:
                Label:
                    text: root.address
                    halign: 'left'
                    valign: 'middle'
                    text_size: self.width - dp(16), None
                    shorten: True
                    shorten_from: 'right'
                    padding: [dp(8), 0]
            Button:
                text: "Copy"
                size_hint_x: None
                width: '70dp'
                on_release: app.copy_receive_address()
            Button:
                text: "New"
                size_hint_x: None
                width: '60dp'
                on_release: app.generate_new_receive_address()


    BoxLayout:
        orientation: 'vertical'
        size_hint_y: None
        height: self.minimum_height
        Label:
            text: 'Balance:'
            size_hint_y: None
            height: self.texture_size[1]
            halign: 'left'
            valign: 'middle'
        Label:
            text: root.balance
            size_hint_y: None
            height: '40dp'
        Label:
            text: root.status
            size_hint_y: None
            height: '30dp'

    # RECENT TRANSACTIONS
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: 1
        spacing: '4dp'
        Label:
            text: 'Recent Transactions:'
            size_hint_y: None
            height: self.texture_size[1]
            halign: 'left'
            valign: 'middle'
        ScrollView:
            do_scroll_x: False
            do_scroll_y: True
            GridLayout:
                id: tx_grid
                cols: 1
                size_hint_y: None
                height: self.minimum_height


    # SEND
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: None
        height: self.minimum_height
        Label:
            text: 'Send To Address:'
            size_hint_y: None
            height: self.texture_size[1]
        TextInputFixed:
            id: send_to_input
            text: root.send_to
            on_text: root.send_to = self.text
            multiline: False
            size_hint_y: None
            height: '40dp'
            on_text_validate: amount_input.focus = True
            keyboard_mode: 'managed'

    BoxLayout:
        orientation: 'vertical'
        size_hint_y: None
        height: self.minimum_height
        Label:
            text: 'Amount (FREN):'
            size_hint_y: None
            height: self.texture_size[1]
        TextInputFixed:
            id: amount_input
            text: root.amount
            on_text: root.amount = self.text
            multiline: False
            input_filter: 'float'
            size_hint_y: None
            height: '40dp'
            keyboard_mode: 'managed'

    BoxLayout:
        size_hint_y: None
        height: '44dp'
        spacing: '10dp'
        Button:
            text: 'Refresh'
            on_release: app.refresh_and_sync()
        Button:
            text: 'Send'
            on_release: app.send_funds(root.send_to, root.amount)

<RestoreWalletPopup>:
    title: "Welcome fren !!!!!!"
    size_hint: .9, .9
    auto_dismiss: False
    ScrollView:
        id: restore_scroll
        do_scroll_x: False
        do_scroll_y: True

        BoxLayout:
            orientation: 'vertical'
            padding: '12dp'
            spacing: '12dp'
            size_hint_y: None
            height: self.minimum_height

            Label:
                text: "Restore a Frencoin wallet from a 12-word recovery phrase, or create a new one."
                text_size: self.width, None
                size_hint_y: None
                height: self.texture_size[1]
                halign: 'left'

            Label:
                text: "Recovery phrase:"
                size_hint_y: None
                height: self.texture_size[1]
                halign: 'left'

            TextInput:
                id: seed_input
                hint_text: "Enter 12-word seed here"
                multiline: True
                size_hint_y: None
                height: '120dp'
                on_focus:
                    root.scroll_to_widget(self) if self.focus else None

            Label:
                id: error_label
                text: ""
                color: (1,0,0,1)
                size_hint_y: None
                height: self.texture_size[1]

            BoxLayout:
                size_hint_y: None
                height: '48dp'
                spacing: '12dp'
                Button:
                    text: "Create New Wallet"
                    on_release: root.create_new()
                Button:
                    text: "Restore"
                    on_release: root.restore(seed_input.text)

            AnchorLayout:
                size_hint_y: None
                height: '220dp'
                anchor_x: 'center'
                anchor_y: 'top'
                padding: '0dp', '-20dp', '0dp', '0dp'
                Image:
                    source: 'assets/welcome_fren.png'
                    size_hint: None, None
                    size: '250dp', '250dp'
                    allow_stretch: True
                    keep_ratio: True

<SeedQuizPopup>:
    title: "Confirm your 12-word seed"
    size_hint: .9, .9
    auto_dismiss: False

    BoxLayout:
        orientation: 'vertical'
        padding: '10dp'
        spacing: '8dp'

        # Numbered, nicely formatted masked seed at the top
        ScrollView:
            size_hint_y: None
            height: '120dp'
            do_scroll_x: False
            do_scroll_y: True
            Label:
                text: root.display_seed
                text_size: self.width, None
                size_hint_y: None
                height: self.texture_size[1]
                halign: 'center'

        Label:
            text: "Type the missing words in order:"
            size_hint_y: None
            height: self.texture_size[1]

        BoxLayout:
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            spacing: '8dp'
            TextInputFixed:
                id: w1
                hint_text: "Missing word #1"
                multiline: False
                size_hint_y: None
                height: '40dp'
                on_text_validate: w2.focus = True
                keyboard_mode: 'managed'
            TextInputFixed:
                id: w2
                hint_text: "Missing word #2"
                multiline: False
                size_hint_y: None
                height: '40dp'
                on_text_validate: w3.focus = True
                keyboard_mode: 'managed'
            TextInputFixed:
                id: w3
                hint_text: "Missing word #3"
                multiline: False
                size_hint_y: None
                height: '40dp'
                on_text_validate: root.check([w1.text, w2.text, w3.text])
                keyboard_mode: 'managed'

        Label:
            text: root.error_text
            color: (1, 0, 0, 1)
            size_hint_y: None
            height: self.texture_size[1]

        BoxLayout:
            size_hint_y: None
            height: '44dp'
            spacing: '10dp'
            Button:
                text: "Back"
                on_release: root.back_to_seed_view()
            Button:
                text: "Confirm"
                on_release: root.check([w1.text, w2.text, w3.text])

        # Spacer to reserve room for keyboard - content stays above
        Widget:
            size_hint_y: 1

<SeedViewPopup>:
    title: "Write down your recovery phrase"
    size_hint: .9, .7
    auto_dismiss: False

    BoxLayout:
        orientation: 'vertical'
        padding: '10dp'
        spacing: '8dp'

        Label:
            text: "Write this 12-word phrase on paper and keep it in a safe place."
            text_size: self.width, None
            size_hint_y: None
            height: self.texture_size[1]

        Label:
            text: "WARNING:"
            font_size: '24sp'
            bold: True
            color: (1, 0, 0, 1)
            size_hint_y: None
            height: self.texture_size[1]
            halign: 'center'

        Label:
            text: "IF U LOSE UR WORDS U MIGHT LOSE UR FRENS!!!!!"
            text_size: self.width, None
            size_hint_y: None
            height: self.texture_size[1]
            color: (1, 0.3, 0.3, 1)
            halign: 'center'

        Label:
            text: root.formatted_seed
            font_size: '16sp'
            text_size: self.width, None
            size_hint_y: None
            height: self.texture_size[1]
            halign: 'center'

        Image:
            source: 'assets/seed_backup.png'
            size_hint: None, None
            size: '200dp', '200dp'
            pos_hint: {'center_x': 0.5}
            allow_stretch: True
            keep_ratio: True

        Widget:
            size_hint_y: 1

        BoxLayout:
            size_hint_y: None
            height: '44dp'
            spacing: '10dp'
            Widget:
                size_hint_x: 1
            Button:
                text: "Continue to quiz"
                size_hint_x: None
                width: '160dp'
                on_release: root.continue_to_quiz()

<SeedViewFromMenuPopup>:
    title: "Your recovery phrase"
    size_hint: .9, .7
    auto_dismiss: True

    BoxLayout:
        orientation: 'vertical'
        padding: '10dp'
        spacing: '8dp'

        Label:
            text: "Keep this 12-word phrase safe. Anyone with this phrase can access your wallet."
            text_size: self.width, None
            size_hint_y: None
            height: self.texture_size[1]

        Label:
            text: root.formatted_seed
            font_size: '16sp'
            text_size: self.width, None
            size_hint_y: None
            height: self.texture_size[1]
            halign: 'center'

        Image:
            source: 'assets/seed_backup2.png'
            size_hint: None, None
            size: '200dp', '200dp'
            pos_hint: {'center_x': 0.5}
            allow_stretch: True
            keep_ratio: True

        Widget:
            size_hint_y: 1

        BoxLayout:
            size_hint_y: None
            height: '44dp'
            spacing: '10dp'
            Widget:
                size_hint_x: 1
            Button:
                text: "Close"
                size_hint_x: None
                width: '100dp'
                on_release: root.dismiss()


<MenuPopup>:
    title: "Menu"
    size_hint: .8, .5
    auto_dismiss: True

    BoxLayout:
        orientation: 'vertical'
        padding: '10dp'
        spacing: '10dp'

        Button:
            text: "View recovery phrase"
            size_hint_y: None
            height: '48dp'
            on_release: root.view_recovery_phrase()

        Button:
            text: "Set/Change password"
            size_hint_y: None
            height: '48dp'
            on_release: app.open_password_dialog()

        Button:
            text: "Fee settings"
            size_hint_y: None
            height: '48dp'
            on_release: app.open_fee_settings()

        Button:
            text: "Previous addresses"
            size_hint_y: None
            height: '48dp'
            on_release: root.view_addresses()

        Widget:

        Button:
            text: "Close"
            size_hint_y: None
            height: '48dp'
            on_release: root.dismiss()

<AddressListPopup>:
    title: "Previous Addresses"
    size_hint: .95, .9
    auto_dismiss: True

    BoxLayout:
        orientation: 'vertical'
        padding: '10dp'
        spacing: '10dp'

        Label:
            text: "Tap to copy"
            text_size: self.width, None
            size_hint_y: None
            height: self.texture_size[1]
            halign: 'left'

        ScrollView:
            do_scroll_x: False
            do_scroll_y: True
            GridLayout:
                id: addr_grid
                cols: 1
                size_hint_y: None
                height: self.minimum_height
                spacing: '4dp'

        Button:
            text: "Close"
            size_hint_y: None
            height: '48dp'
            on_release: root.dismiss()

<NoPasswordWarningPopup>:
    title: ""
    separator_height: 0
    size_hint: .9, .7
    auto_dismiss: False
    BoxLayout:
        orientation: 'vertical'
        padding: '15dp'
        spacing: '10dp'

        Label:
            text: "WARNING"
            font_size: '24sp'
            bold: True
            color: (1, 0, 0, 1)
            size_hint_y: None
            height: self.texture_size[1]
            halign: 'center'

        Label:
            text: "Not setting a password allows anyone with access to your device or backups to extract the wallet file and steal all your frens. You are strongly advised to set one."
            text_size: self.width, None
            size_hint_y: None
            height: self.texture_size[1]
            color: (1, 0.3, 0.3, 1)
            halign: 'center'

        Image:
            source: 'assets/no_password_warning.png'
            size_hint: None, None
            size: '280dp', '280dp'
            pos_hint: {'center_x': 0.5}
            allow_stretch: True
            keep_ratio: True

        Widget:
            size_hint_y: 1

        BoxLayout:
            size_hint_y: None
            height: '48dp'
            spacing: '10dp'
            Button:
                text: "Back"
                on_release: root.go_back()
            Button:
                text: "I'll take my chances"
                on_release: root.proceed_without_password()

<SetPasswordPopup>:
    title: "Set or change password"
    size_hint: .9, .7
    auto_dismiss: True
    ScrollView:
        id: pw_scroll
        do_scroll_x: False
        do_scroll_y: True

        BoxLayout:
            orientation: 'vertical'
            padding: '10dp'
            spacing: '10dp'
            size_hint_y: None
            height: self.minimum_height

            Label:
                text: "Set a password to encrypt your wallet file."
                size_hint_y: None
                height: self.texture_size[1]

            TextInputFixed:
                id: old_pw
                hint_text: "Current password"
                password: True
                multiline: False
                size_hint_y: None
                height: '0dp' if root.first_time_setup else '40dp'
                opacity: 0 if root.first_time_setup else 1
                disabled: root.first_time_setup
                on_text_validate: root.focus_next('new_pw')
                keyboard_mode: 'managed'

            TextInputFixed:
                id: new_pw
                hint_text: "New password"
                password: True
                multiline: False
                size_hint_y: None
                height: '40dp'
                on_text_validate: root.focus_next('confirm_pw')
                keyboard_mode: 'managed'

            TextInputFixed:
                id: confirm_pw
                hint_text: "Confirm new password"
                password: True
                multiline: False
                size_hint_y: None
                height: '40dp'
                on_text_validate: root.save(old_pw.text, new_pw.text, confirm_pw.text)
                keyboard_mode: 'managed'

            Label:
                id: err
                text: ""
                color: (1,0,0,1)
                size_hint_y: None
                height: self.texture_size[1]

            BoxLayout:
                size_hint_y: None
                height: '44dp'
                spacing: '10dp'
                Widget:
                    size_hint_x: 1
                Button:
                    text: "Save"
                    size_hint_x: None
                    width: '100dp'
                    on_release: root.save(old_pw.text, new_pw.text, confirm_pw.text)

<EnterPasswordPopup>:
    title: "Enter wallet password"
    size_hint: .8, .5
    auto_dismiss: False
    BoxLayout:
        orientation: 'vertical'
        padding: '10dp'
        spacing: '10dp'

        TextInputFixed:
            id: pw
            hint_text: "Password"
            password: True
            multiline: False
            size_hint_y: None
            height: '40dp'
            on_text_validate: root.submit(pw.text)
            keyboard_mode: 'managed'

        Label:
            id: err
            text: ""
            color: (1,0,0,1)
            size_hint_y: None
            height: self.texture_size[1]

        Widget:

        BoxLayout:
            size_hint_y: None
            height: '44dp'
            spacing: '10dp'
            Button:
                text: "Cancel"
                on_release: root.dismiss()
            Button:
                text: "Confirm"
                on_release: root.submit(pw.text)

<ConfirmSendPopup>:
    title: "Confirm send"
    size_hint: .95, .9
    auto_dismiss: False
    BoxLayout:
        orientation: 'vertical'
        padding: '10dp'
        spacing: '10dp'

        Label:
            text: "Please confirm your transaction"
            size_hint_y: None
            height: self.texture_size[1]

        BoxLayout:
            size_hint_y: None
            height: '30dp'
            Label:
                text: "To:"
                size_hint_x: None
                width: '50dp'
            Label:
                id: to_label
                text: root.to_addr or ""

        BoxLayout:
            size_hint_y: None
            height: '30dp'
            Label:
                text: "Amount:"
                size_hint_x: None
                width: '80dp'
            Label:
                id: amt_label
                text: root.amount_text or ""

        Label:
            text: "Fee rate:"
            size_hint_y: None
            height: self.texture_size[1]

        Label:
            text: root.fee_descriptor(fee_slider.value)
            size_hint_y: None
            height: self.texture_size[1]

        Image:
            source: root.fee_image(fee_slider.value)
            size_hint: None, None
            size: '120dp', '120dp'
            pos_hint: {'center_x': 0.5}
            allow_stretch: True
            keep_ratio: True

        Slider:
            id: fee_slider
            min: 0.01
            max: 0.2
            step: 0.00001
            value: root.default_feerate or 0.014

        BoxLayout:
            size_hint_y: None
            height: '32dp'
            spacing: '4dp'
            Button:
                text: "Slow"
                size_hint_x: 0.25
                on_release: fee_slider.value = 0.01
            Button:
                text: "Normal"
                size_hint_x: 0.25
                on_release: fee_slider.value = 0.014
            Button:
                text: "Fast"
                size_hint_x: 0.25
                on_release: fee_slider.value = 0.05
            Button:
                text: "Extreme"
                size_hint_x: 0.25
                on_release: fee_slider.value = 0.2

        BoxLayout:
            size_hint_y: None
            height: '36dp'
            spacing: '10dp'
            CheckBox:
                id: subtract_cb
                size_hint_x: None
                width: '30dp'
                active: root.subtract_fee
            Button:
                text: "Subtract fee from amount"
                background_color: 0, 0, 0, 0
                size_hint_x: 1
                halign: 'left'
                valign: 'middle'
                text_size: self.width - dp(10), None
                on_release: setattr(subtract_cb, 'active', not subtract_cb.active)

        BoxLayout:
            size_hint_y: None
            height: '36dp'
            spacing: '10dp'
            CheckBox:
                id: dont_show_cb
                size_hint_x: None
                width: '30dp'
                active: False
            Button:
                text: "Don't show this confirmation again"
                background_color: 0, 0, 0, 0
                size_hint_x: 1
                halign: 'left'
                valign: 'middle'
                text_size: self.width - dp(10), None
                on_release: setattr(dont_show_cb, 'active', not dont_show_cb.active)

        Widget:

        BoxLayout:
            size_hint_y: None
            height: '44dp'
            spacing: '10dp'
            Button:
                text: "Cancel"
                on_release: root.dismiss()
            Button:
                text: "Confirm"
                on_release: root.confirm(fee_slider.value, subtract_cb.active, dont_show_cb.active)

<FeeSettingsPopup>:
    title: "Fee settings"
    size_hint: .95, .8
    auto_dismiss: True
    BoxLayout:
        orientation: 'vertical'
        padding: '10dp'
        spacing: '10dp'

        Label:
            text: "Default fee rate:"
            size_hint_y: None
            height: self.texture_size[1]

        Label:
            text: root.fee_descriptor(fee_slider.value)
            size_hint_y: None
            height: self.texture_size[1]

        Image:
            source: root.fee_image(fee_slider.value)
            size_hint: None, None
            size: '120dp', '120dp'
            pos_hint: {'center_x': 0.5}
            allow_stretch: True
            keep_ratio: True

        Slider:
            id: fee_slider
            min: 0.01
            max: 0.2
            step: 0.00001
            value: root.default_feerate or 0.014

        BoxLayout:
            size_hint_y: None
            height: '32dp'
            spacing: '4dp'
            Button:
                text: "Slow"
                size_hint_x: 0.25
                on_release: fee_slider.value = 0.01
            Button:
                text: "Normal"
                size_hint_x: 0.25
                on_release: fee_slider.value = 0.014
            Button:
                text: "Fast"
                size_hint_x: 0.25
                on_release: fee_slider.value = 0.05
            Button:
                text: "Extreme"
                size_hint_x: 0.25
                on_release: fee_slider.value = 0.2

        BoxLayout:
            size_hint_y: None
            height: '36dp'
            spacing: '10dp'
            CheckBox:
                id: subtract_cb
                size_hint_x: None
                width: '30dp'
                active: root.subtract_fee
            Button:
                text: "Subtract fee from amount"
                background_color: 0, 0, 0, 0
                size_hint_x: 1
                halign: 'left'
                valign: 'middle'
                text_size: self.width - dp(10), None
                on_release: setattr(subtract_cb, 'active', not subtract_cb.active)

        BoxLayout:
            size_hint_y: None
            height: '36dp'
            spacing: '10dp'
            CheckBox:
                id: skip_cb
                size_hint_x: None
                width: '30dp'
                active: root.skip_confirm
            Button:
                text: "Don't show confirmation before sending"
                background_color: 0, 0, 0, 0
                size_hint_x: 1
                halign: 'left'
                valign: 'middle'
                text_size: self.width - dp(10), None
                on_release: setattr(skip_cb, 'active', not skip_cb.active)

        Widget:

        BoxLayout:
            size_hint_y: None
            height: '44dp'
            spacing: '10dp'
            Button:
                text: "Close"
                on_release: root.save_and_close(fee_slider.value, subtract_cb.active, skip_cb.active)
"""


class MainScreen(BoxLayout):
    status = StringProperty("Starting…")
    address = StringProperty("")
    balance = StringProperty("Unknown")
    send_to = StringProperty("")
    amount = StringProperty("")
    quiz_completed = BooleanProperty(False)

    def update_transactions(self, tx_list):
        grid = self.ids.get("tx_grid") if hasattr(self, "ids") else None
        if not grid:
            return

        grid.clear_widgets()

        # Header
        header = BoxLayout(size_hint_y=None, height="28dp", spacing="6dp")
        header.add_widget(Label(text="[b]Date[/b]", markup=True, size_hint_x=0.25))
        header.add_widget(Label(text="[b]TXID[/b]", markup=True, size_hint_x=0.45))
        header.add_widget(Label(text="[b]Type[/b]", markup=True, size_hint_x=0.15))
        header.add_widget(Label(text="[b]Amount[/b]", markup=True, size_hint_x=0.15))
        grid.add_widget(header)

        if not tx_list:
            grid.add_widget(
                Label(
                    text="No transactions yet.",
                    size_hint_y=None,
                    height="24dp",
                    halign="left",
                    valign="middle",
                )
            )
            return

        from kivy.graphics import Color, Rectangle

        def add_bottom_border(w):
            def _update(_inst, *args):
                w.canvas.after.clear()
                with w.canvas.after:
                    Color(0.6, 0.6, 0.6, 1)
                    Rectangle(pos=(w.x, w.y), size=(w.width, 1))

            w.bind(pos=_update, size=_update)
            _update(w)

        add_bottom_border(header)

        def add_bg(w, dir_ch):
            def _update(_inst, *args):
                w.canvas.before.clear()
                with w.canvas.before:
                    if dir_ch == "R":
                        Color(0, 1, 0, 0.15)
                    elif dir_ch == "S":
                        Color(1, 0, 0, 0.15)
                    else:
                        Color(0, 0, 0, 0)
                    Rectangle(pos=w.pos, size=w.size)

            w.bind(pos=_update, size=_update)
            _update(w)

        for tx in tx_list:
            date = (tx.get("date") or "")[:10]
            txid = tx.get("txid") or ""
            if len(txid) > 16:
                txid_disp = f"{txid[:8]}…{txid[-8:]}"
            else:
                txid_disp = txid
            direction = tx.get("direction") or ""
            direction = (
                "R" if direction == "IN" else ("S" if direction == "OUT" else "")
            )
            amount = tx.get("amount") or ""

            row = BoxLayout(size_hint_y=None, height="36dp", spacing="6dp")
            row.add_widget(
                DateButton(
                    text=date, full_text=tx.get("full_date") or "", size_hint_x=0.25
                )
            )
            btn = TxIdButton(text=txid_disp, txid=txid, size_hint_x=0.45)
            row.add_widget(btn)
            row.add_widget(Label(text=direction, size_hint_x=0.15))
            row.add_widget(Label(text=amount, size_hint_x=0.15))
            add_bg(row, direction)
            grid.add_widget(row)
            add_bottom_border(row)


class SeedQuizPopup(Popup):
    full_seed = StringProperty("")
    display_seed = StringProperty("")
    missing_indices = ListProperty([])
    error_text = StringProperty("")

    def on_open(self):
        # Use resize mode to prevent screen jumping - the layout has a spacer
        # at the bottom to reserve room for the keyboard
        try:
            self._prev_softinput = Window.softinput_mode
            Window.softinput_mode = "resize"
        except Exception:
            pass

    def on_dismiss(self):
        # Restore previous softinput mode
        try:
            if hasattr(self, "_prev_softinput"):
                Window.softinput_mode = self._prev_softinput
        except Exception:
            pass
        # Don't clear if navigating back to seed view (seed still needed)
        if getattr(self, '_going_back_to_seed', False):
            self._going_back_to_seed = False
            self.full_seed = ""
            self.display_seed = ""
            return
        # Securely clear seed from memory
        secure_clear_string(self.full_seed)
        secure_clear_string(self.display_seed)
        self.full_seed = ""
        self.display_seed = ""

    def check(self, answers):
        words = self.full_seed.split()
        for user_word, idx in zip(answers, self.missing_indices):
            if user_word.strip().lower() != words[idx].lower():
                self.error_text = "One or more words are incorrect. Try again."
                return

        self.error_text = ""
        self.dismiss()
        app = App.get_running_app()
        if app and hasattr(app, "on_seed_quiz_completed"):
            app.on_seed_quiz_completed()

    def back_to_seed_view(self):
        """
        Go back to the 'view seed' popup so the user can re-read the phrase.
        When they hit 'Continue to quiz' again, a fresh quiz is generated.
        """
        app = App.get_running_app()
        # Create a true copy of seed before dismiss clears it
        seed = str(self.full_seed)
        self._going_back_to_seed = True  # Flag to skip clearing on dismiss
        self.dismiss()
        if app and hasattr(app, "open_seed_backup_flow"):
            app.open_seed_backup_flow(seed)


class SeedViewPopup(Popup):
    full_seed = StringProperty("")
    formatted_seed = StringProperty("")

    def on_full_seed(self, instance, value):
        # Build a 4-column numbered layout once the seed is assigned
        normalized = " ".join((value or "").split())
        self.formatted_seed = format_seed_3col(normalized)

    def continue_to_quiz(self):
        app = App.get_running_app()
        # Create a true copy of seed (not just a reference) before dismiss clears it
        seed = str(self.full_seed)
        self._continuing_to_quiz = True  # Flag to skip clearing on dismiss
        self.dismiss()
        app.open_seed_quiz(seed)

    def on_dismiss(self):
        # Don't clear if we're continuing to quiz (seed still needed)
        if getattr(self, '_continuing_to_quiz', False):
            self._continuing_to_quiz = False
            self.full_seed = ""
            self.formatted_seed = ""
            return
        # Securely clear seed from memory
        secure_clear_string(self.full_seed)
        secure_clear_string(self.formatted_seed)
        self.full_seed = ""
        self.formatted_seed = ""


class SeedViewFromMenuPopup(Popup):
    """Separate popup for viewing seed from menu - always has Close button."""

    full_seed = StringProperty("")
    formatted_seed = StringProperty("")

    def on_full_seed(self, instance, value):
        normalized = " ".join((value or "").split())
        self.formatted_seed = format_seed_3col(normalized)

    def on_dismiss(self, *args):
        # Clear on the next frame, when we're no longer visible
        Clock.schedule_once(self._clear_seed, 0)

    def _clear_seed(self, dt):
        # Securely clear seed from memory
        secure_clear_string(self.full_seed)
        secure_clear_string(self.formatted_seed)
        self.full_seed = ""
        self.formatted_seed = ""


class MenuPopup(Popup):
    def view_recovery_phrase(self):
        app = App.get_running_app()
        self.dismiss()
        if app and hasattr(app, "open_view_seed_from_menu"):
            app.open_view_seed_from_menu()

    def view_addresses(self):
        app = App.get_running_app()
        self.dismiss()
        if app and hasattr(app, "open_address_list"):
            app.open_address_list()


class AddressListPopup(Popup):
    def on_open(self):
        self.refresh_address_list()

    def refresh_address_list(self):
        grid = self.ids.get("addr_grid")
        if not grid:
            return
        grid.clear_widgets()

        app = App.get_running_app()
        if not app or not app.wallet:
            grid.add_widget(
                Label(
                    text="Wallet not ready.",
                    size_hint_y=None,
                    height=dp(40),
                )
            )
            return

        # Get displayed addresses from wallet DB (all addresses that have been shown to user)
        try:
            displayed_addresses = app.wallet.db.get("displayed_addresses", [])
        except Exception:
            displayed_addresses = []

        if not displayed_addresses:
            grid.add_widget(
                Label(
                    text="No previous addresses.\nAddresses will appear here after\ntapping 'New' button.",
                    size_hint_y=None,
                    height=dp(70),
                    halign="center",
                )
            )
            return

        for i, addr in enumerate(
            displayed_addresses[:20]
        ):  # Show up to 20 displayed addresses
            # Format: show index and truncated address
            if len(addr) > 24:
                addr_display = f"{addr[:14]}...{addr[-10:]}"
            else:
                addr_display = addr

            btn = Button(
                text=f"{i+1}. {addr_display}",
                size_hint_y=None,
                height=dp(44),
                halign="left",
                valign="middle",
            )
            btn.bind(
                texture_size=lambda inst, val: setattr(
                    inst, "text_size", (inst.width - dp(20), None)
                )
            )
            btn.addr = addr  # Store full address
            btn.bind(on_release=self.copy_address)
            grid.add_widget(btn)

    def copy_address(self, btn):
        addr = getattr(btn, "addr", "")
        if addr:
            try:
                clipboard_copy_with_timeout(addr, timeout_seconds=60)
                btn.text = "Copied!"
                Clock.schedule_once(lambda dt: self.refresh_address_list(), 1.5)
            except Exception:
                pass


class NoPasswordWarningPopup(Popup):
    """Warning popup shown when user tries to skip setting a password."""

    old_pw = StringProperty("")
    first_time_setup = BooleanProperty(False)

    def go_back(self):
        """Return to password dialog."""
        self.dismiss()
        SetPasswordPopup(first_time_setup=self.first_time_setup).open()

    def proceed_without_password(self):
        """User accepted the risk, proceed without password."""
        self.dismiss()
        app = App.get_running_app()
        if app and hasattr(app, "set_wallet_password"):
            app.set_wallet_password(self.old_pw or None, None)


class SetPasswordPopup(Popup):
    # If True, hide current password field (used only for first-time setup after wallet creation)
    first_time_setup = BooleanProperty(False)

    def save(self, old_pw, new_pw, confirm_pw):
        if (new_pw or "").strip() != (confirm_pw or "").strip():
            try:
                self.ids.err.text = "Passwords do not match."
            except Exception:
                pass
            return

        new_pw_stripped = (new_pw or "").strip()
        old_pw_stripped = (old_pw or "").strip() or None

        app = App.get_running_app()

        # Check cooldown first
        if app and app._check_password_cooldown():
            return

        # Verify old password first before doing anything else
        if app and app.wallet and app.wallet.has_password():
            try:
                app.wallet.check_password(old_pw_stripped)
            except Exception:
                # Record failed attempt and show wrong password popup
                app._record_failed_password()
                self.dismiss()
                app._error_with_image("Wrong password.", "assets/wrong_password.png")
                return

        # If no new password, show warning popup
        if not new_pw_stripped:
            self.dismiss()
            NoPasswordWarningPopup(
                old_pw=old_pw_stripped or "", first_time_setup=self.first_time_setup
            ).open()
            return

        try:
            if app and hasattr(app, "set_wallet_password"):
                app.set_wallet_password(old_pw_stripped, new_pw_stripped)
                self.dismiss()
            else:
                self.ids.err.text = "App not ready"
        except Exception as e:
            try:
                self.ids.err.text = str(e)
            except Exception:
                pass

    def on_dismiss(self):
        # Restore previous softinput mode if we changed it
        try:
            if hasattr(self, "_prev_softinput_pw"):
                Window.softinput_mode = self._prev_softinput_pw
        except Exception:
            pass

    def focus_next(self, next_id):
        try:
            nxt = self.ids.get(next_id)
            if nxt:
                nxt.focus = True
        except Exception:
            pass

    def scroll_to_widget(self, w):
        try:
            sv = self.ids.get("pw_scroll")
            if not sv:
                return
            from kivy.clock import Clock

            def _do(_dt):
                try:
                    sv.scroll_to(w)
                except Exception:
                    pass

            # debounce slightly to avoid racing IME animations
            Clock.schedule_once(_do, 0.20)
        except Exception:
            pass

    def on_open(self):
        # Prefer below_target for better field stability; fallback to pan
        try:
            self._prev_softinput_pw = Window.softinput_mode
            try:
                Window.softinput_mode = "below_target"
            except Exception:
                Window.softinput_mode = "pan"
        except Exception:
            pass
        try:
            ids = self.ids
            # Auto-focus appropriate field when opening
            if ids.get("old_pw") and ids.get("new_pw") and ids.get("confirm_pw"):
                if not ids["new_pw"].text and not ids["confirm_pw"].text:
                    target = (
                        ids.get("new_pw")
                        if self.first_time_setup
                        else ids.get("old_pw")
                    )
                    Clock.schedule_once(lambda dt: setattr(target, "focus", True), 0.1)
        except Exception:
            pass


class EnterPasswordPopup(Popup):
    submit_cb = ObjectProperty(None, allownone=True)

    def on_open(self):
        # Use resize mode so keyboard doesn't push the popup off screen
        try:
            self._prev_softinput = Window.softinput_mode
            Window.softinput_mode = "resize"
        except Exception:
            pass

    def on_dismiss(self):
        # Restore previous softinput mode
        try:
            if hasattr(self, "_prev_softinput"):
                Window.softinput_mode = self._prev_softinput
        except Exception:
            pass

    def submit(self, pw):
        """Called when user submits password."""
        cb = self.submit_cb
        self.dismiss()
        if cb:
            try:
                cb((pw or "").strip() or None)
            except Exception:
                pass


class ConfirmSendPopup(Popup):
    to_addr = StringProperty("")
    amount_text = StringProperty("")
    default_feerate = NumericProperty(5)
    subtract_fee = BooleanProperty(False)

    def fee_image(self, v):
        """Return the image path for the current fee level."""
        try:
            v = float(v)
        except Exception:
            v = 0.014
        if v <= 0.01000:
            return "assets/fee_slow.png"
        elif v <= 0.02000:
            return "assets/fee_normal.png"
        elif v <= 0.10000:
            return "assets/fee_fast.png"
        else:
            return "assets/fee_extreme.png"

    def fee_descriptor(self, v):
        try:
            v = float(v)
        except Exception:
            v = 0.014
        # v is already FREN/kB
        fren_kb = float(v)
        if fren_kb <= 0.01000:
            speed = "Show up whenever"
        elif fren_kb <= 0.02000:
            speed = "Normal"
        elif fren_kb <= 0.10000:
            speed = "Fast"
        else:
            speed = "IT'S MY MONEY AND I NEED IT NOW!!!!"
        return f"{speed} • {fren_kb:.5f} FREN/kB"

    def on_open(self):
        try:
            app = App.get_running_app()
            params = getattr(app, "_pending_send", None)
            if params:
                dest_addr, amount = params
                self.to_addr = dest_addr
                self.amount_text = f"{amount} FREN"
        except Exception:
            pass

    def confirm(self, feerate_value, subtract, dont_show):
        app = App.get_running_app()
        try:
            if app and hasattr(app, "_proceed_after_confirm"):
                app._proceed_after_confirm(
                    float(feerate_value), bool(subtract), bool(dont_show)
                )
        finally:
            self.dismiss()


class FeeSettingsPopup(Popup):
    default_feerate = NumericProperty(5)
    subtract_fee = BooleanProperty(False)
    skip_confirm = BooleanProperty(False)

    def fee_image(self, v):
        """Return the image path for the current fee level."""
        try:
            v = float(v)
        except Exception:
            v = 0.014
        if v <= 0.01000:
            return "assets/fee_slow.png"
        elif v <= 0.02000:
            return "assets/fee_normal.png"
        elif v <= 0.10000:
            return "assets/fee_fast.png"
        else:
            return "assets/fee_extreme.png"

    def fee_descriptor(self, v):
        try:
            v = float(v)
        except Exception:
            v = 0.014
        # v is already FREN/kB
        fren_kb = float(v)
        if fren_kb <= 0.01000:
            speed = "Show up whenever"
        elif fren_kb <= 0.02000:
            speed = "Normal"
        elif fren_kb <= 0.10000:
            speed = "Fast"
        else:
            speed = "IT'S MY MONEY AND I NEED IT NOW!!!!"
        return f"{speed} • {fren_kb:.5f} FREN/kB"

    def save_and_close(self, feerate_value, subtract, skip_confirm):
        app = App.get_running_app()
        try:
            if app and app.config:
                try:
                    app.config.set_key("default_fee_fren_kb", float(feerate_value))
                    app.config.set_key("subtract_fee", bool(subtract))
                    app.config.set_key("skip_send_confirm", bool(skip_confirm))
                except Exception:
                    pass
        finally:
            self.dismiss()

    def submit(self, pw):
        cb = self.submit_cb
        self.dismiss()
        if cb:
            try:
                cb((pw or "").strip() or None)
            except Exception:
                pass
        else:
            app = App.get_running_app()
            if app and hasattr(app, "_finish_send_with_password"):
                app._finish_send_with_password((pw or "").strip() or None)


class TxIdButton(Button):
    txid = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)
        self.color = (0.2, 0.5, 0.9, 1)

    def on_release(self):
        app = App.get_running_app()
        if app and self.txid and hasattr(app, "open_transaction_in_explorer"):
            try:
                app.open_transaction_in_explorer(self.txid)
            except Exception:
                pass


class DateButton(Button):
    full_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = (0, 0, 0, 0)

    def on_release(self):
        if not self.full_text:
            return
        try:
            Popup(
                title="Date/Time",
                content=Label(text=self.full_text),
                size_hint=(0.8, 0.3),
            ).open()
        except Exception:
            pass


class PasteTextInput(TextInput):
    prevent_collapse = BooleanProperty(True)
    _lp_ev = None

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._start_long_press()
        return super().on_touch_down(touch)

    def on_touch_up(self, touch):
        self._cancel_long_press()
        return super().on_touch_up(touch)

    def _start_long_press(self):
        from kivy.clock import Clock

        # Debounced long-press to open a simple paste menu without collapsing IME
        self._cancel_long_press()
        self._lp_ev = Clock.schedule_once(lambda dt: self._show_paste_menu(), 0.35)

    def _cancel_long_press(self):
        if self._lp_ev:
            self._lp_ev.cancel()
            self._lp_ev = None

    def _show_paste_menu(self):
        # Keep focus so the keyboard stays up; present a lightweight Paste action.
        try:
            self.focus = True
        except Exception:
            pass
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.button import Button
        from kivy.uix.popup import Popup

        box = BoxLayout(orientation="vertical", padding="8dp", spacing="8dp")
        paste_btn = Button(text="Paste", size_hint=(1, None), height="44dp")

        def do_paste(_inst):
            try:
                self.paste()
            finally:
                pop.dismiss()

        paste_btn.bind(on_release=do_paste)
        box.add_widget(paste_btn)
        pop = Popup(title="", content=box, size_hint=(0.5, 0.2), auto_dismiss=True)
        pop.open()


class AddressBox(BoxLayout):
    """A styled gray box for displaying the wallet address."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        from kivy.graphics import Color, RoundedRectangle

        with self.canvas.before:
            Color(0.25, 0.25, 0.25, 1)  # Dark gray background
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(5)])
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size


# Register AddressBox with Factory
Factory.register("AddressBox", cls=AddressBox)


class TextInputFixed(TextInput):
    """
    Close port of the GitHub workaround: managed keyboard, delayed show, and
    focus drop when touching outside to avoid hide/show races.
    """

    def on_focus(self, instance, value, *args):
        if value:
            Clock.schedule_once(self.create_keyboard, 0.1)
        else:
            self.hide_keyboard()

    def create_keyboard(self, *args):
        self.show_keyboard()

    def remove_focus_decorator(function):
        def wrapper(self, touch):
            if not self.collide_point(*touch.pos):
                self.focus = False
            function(self, touch)

        return wrapper

    @remove_focus_decorator
    def on_touch_down(self, touch):
        super().on_touch_down(touch)


# Register custom widgets with Factory so KV can find them
Factory.register("TextInputFixed", cls=TextInputFixed)


class AddressTextInput(TextInputFixed):
    """
    TextInput for address entry with long-press paste support.
    Shows a simple paste popup on long press.
    Inherits from TextInputFixed for keyboard stability.
    """

    _lp_ev = None
    _touch_start_pos = None

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            self._touch_start_pos = touch.pos
            self._start_long_press(touch)
        return super().on_touch_down(touch)

    def on_touch_move(self, touch):
        # Cancel long press if finger moves significantly
        if self._touch_start_pos and self.collide_point(*touch.pos):
            dx = abs(touch.pos[0] - self._touch_start_pos[0])
            dy = abs(touch.pos[1] - self._touch_start_pos[1])
            if dx > dp(10) or dy > dp(10):
                self._cancel_long_press()
        return super().on_touch_move(touch)

    def on_touch_up(self, touch):
        self._cancel_long_press()
        self._touch_start_pos = None
        return super().on_touch_up(touch)

    def _start_long_press(self, touch):
        self._cancel_long_press()
        self._lp_ev = Clock.schedule_once(lambda dt: self._show_paste_menu(), 0.4)

    def _cancel_long_press(self):
        if self._lp_ev:
            self._lp_ev.cancel()
            self._lp_ev = None

    def _show_paste_menu(self):
        self._long_press_triggered = True
        # Ensure we maintain focus
        self.focus = True

        box = BoxLayout(orientation="horizontal", padding="8dp", spacing="8dp")

        paste_btn = Button(text="Paste", size_hint=(1, None), height="44dp")
        clear_btn = Button(text="Clear", size_hint=(1, None), height="44dp")

        def do_paste(_inst):
            try:
                self.paste()
            finally:
                pop.dismiss()

        def do_clear(_inst):
            self.text = ""
            pop.dismiss()

        paste_btn.bind(on_release=do_paste)
        clear_btn.bind(on_release=do_clear)
        box.add_widget(paste_btn)
        box.add_widget(clear_btn)

        pop = Popup(
            title="",
            content=box,
            size_hint=(0.6, None),
            height=dp(80),
            auto_dismiss=True,
            separator_height=0,
        )
        pop.open()


# Register AddressTextInput with Factory
Factory.register("AddressTextInput", cls=AddressTextInput)


class RestoreWalletPopup(Popup):
    def on_open(self):
        # Prefer 'below_target' for best UX; fallback to 'pan'.
        try:
            self._prev_softinput = Window.softinput_mode
            try:
                Window.softinput_mode = "below_target"
            except Exception:
                Window.softinput_mode = "pan"
        except Exception:
            pass
        # add gentle padding to the seed field
        try:
            if "seed_input" in self.ids:
                self.ids.seed_input.padding = [dp(8), dp(10)]
        except Exception:
            pass

    def _on_sv_size(self, *args):
        # No-op: rely on single debounced scroll_to on focus
        pass

    def _on_window_size(self, *args):
        # No-op: rely on global 'pan' and focus-driven scroll
        pass

    def on_dismiss(self):
        # Restore softinput_mode and unbind window handlers
        try:
            if hasattr(self, "_win_bound") and self._win_bound:
                Window.unbind(size=self._on_window_size)
                self._win_bound = False
        except Exception:
            pass
        try:
            if hasattr(self, "_prev_softinput"):
                Window.softinput_mode = self._prev_softinput
        except Exception:
            pass

    def _on_seed_focus(self, instance, value):
        # Track focused widget and scroll it into view
        try:
            if value:
                self._focused = instance
                self.scroll_to_widget(instance)
        except Exception:
            pass

    def restore(self, seed_text: str):
        app = App.get_running_app()
        seed = (seed_text or "").strip()
        if not seed:
            self.ids.error_label.text = "Seed cannot be empty."
            return
        words = seed.split()
        if len(words) < 12:
            self.ids.error_label.text = "Seed must be at least 12 words."
            return
        try:
            if app and hasattr(app, "_restore_wallet_from_seed"):
                app._restore_wallet_from_seed(seed)
                self.dismiss()
            else:
                self.ids.error_label.text = "App not ready"
        except Exception as e:
            self.ids.error_label.text = f"Restore error: {e}"

    def create_new(self):
        app = App.get_running_app()
        try:
            if app and hasattr(app, "_create_new_wallet"):
                app._create_new_wallet()
                self.dismiss()
            else:
                self.ids.error_label.text = "App not ready"
        except Exception as e:
            self.ids.error_label.text = f"Error: {e}"

    def scroll_to_widget(self, w):
        # Debounce and re-scroll while keyboard animates, preserving scroll_y
        try:
            sv = self.ids.restore_scroll
            self._sv_last_scroll_y = sv.scroll_y
        except Exception:
            pass

        def scroll_to_widget(self, w):
            # Single debounced scroll with padding and no animation to prevent jumping
            try:
                if hasattr(self, "_scroll_ev") and self._scroll_ev is not None:
                    self._scroll_ev.cancel()
            except Exception:
                pass

            def _do_scroll(_dt):
                try:
                    sv = self.ids.restore_scroll
                    sv.scroll_to(w, padding=dp(12), animate=False)
                except Exception:
                    pass

            try:
                from kivy.clock import Clock

                self._scroll_ev = Clock.schedule_once(_do_scroll, 0.18)
            except Exception:
                _do_scroll(0)


class FrencoinApp(App):
    # Cache for transaction timestamps fetched from block explorer
    # Maps txid -> unix timestamp
    _tx_timestamp_cache = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.wallet = None
        self.network = None
        self.config = None
        self.seed_quiz_done = False
        self._last_seed_phrase = None
        self.main_screen = None
        self._pending_send = None
        self._pending_feerate = 5
        self._pending_subtract = False
        self._current_display_address = None  # Stable address shown in UI
        # Password attempt tracking for brute-force protection
        # These will be loaded from persistent storage in _init_wallet
        self._failed_password_attempts = 0
        self._password_cooldown_until = 0  # Unix timestamp when cooldown ends
        self._security_state_file = None  # Path to security state file

    def build(self):
        # Use 'pan' mode so keyboard pushes content up when needed
        Window.softinput_mode = "pan"
        # Disable Kivy's built-in virtual keyboard overlay (we use the system keyboard)
        Window.allow_vkeyboard = False
        Builder.load_string(KV)
        self.main_screen = MainScreen()
        return self.main_screen

    def on_start(self):
        # Do wallet/network setup after the UI is visible
        Clock.schedule_once(lambda dt: self._init_wallet(), 0)
        Clock.schedule_interval(lambda dt: self.refresh_wallet(), 15)
        # Periodically save wallet to prevent data loss on crash
        Clock.schedule_interval(lambda dt: self._periodic_wallet_save(), 60)

    def _periodic_wallet_save(self):
        """Periodically save wallet state to disk to prevent data loss."""
        if self.wallet:
            try:
                self.wallet.save_db()
            except Exception:
                pass

    # ---------- Wallet / network setup ----------

    def _get_wallet_dir(self):
        """Get the most reliable wallet directory for the current platform."""
        # Try to use Android's persistent storage first
        android_dir = get_persistent_data_dir()
        if android_dir:
            return android_dir
        # Fallback to Kivy's user_data_dir
        return self.user_data_dir

    def _load_security_state(self):
        """Load brute-force protection state from persistent storage."""
        import time
        import json
        
        if not self._security_state_file:
            return
        
        try:
            if os.path.exists(self._security_state_file):
                with open(self._security_state_file, 'r') as f:
                    data = json.load(f)
                    self._failed_password_attempts = int(data.get('failed_attempts', 0))
                    cooldown_until = float(data.get('cooldown_until', 0))
                    # Only restore cooldown if it hasn't expired
                    if cooldown_until > time.time():
                        self._password_cooldown_until = cooldown_until
                    else:
                        self._password_cooldown_until = 0
        except Exception:
            pass

    def _save_security_state(self):
        """Save brute-force protection state to persistent storage."""
        import json
        
        if not self._security_state_file:
            return
        
        try:
            data = {
                'failed_attempts': self._failed_password_attempts,
                'cooldown_until': self._password_cooldown_until
            }
            with open(self._security_state_file, 'w') as f:
                json.dump(data, f)
            set_secure_file_permissions(self._security_state_file)
        except Exception:
            pass

    def _init_wallet(self):
        self.main_screen.status = "Starting Electrum network…"
        wallet_dir = self._get_wallet_dir()
        os.makedirs(wallet_dir, exist_ok=True)
        set_secure_dir_permissions(wallet_dir)
        wallet_path = os.path.join(wallet_dir, "default_wallet")
        
        # Initialize and load brute-force protection state
        self._security_state_file = os.path.join(wallet_dir, ".security_state")
        self._load_security_state()



        # Check if wallet exists in old location and migrate if needed
        old_wallet_path = os.path.join(self.user_data_dir, "default_wallet")
        if not os.path.exists(wallet_path) and os.path.exists(old_wallet_path) and wallet_dir != self.user_data_dir:
            try:
                import shutil
                os.makedirs(wallet_dir, exist_ok=True)
                set_secure_dir_permissions(wallet_dir)
                shutil.copy2(old_wallet_path, wallet_path)
                set_secure_file_permissions(wallet_path)
            except Exception:
                pass

        # Direct ElectrumX IP + SSL port
        self.config = SimpleConfig(
            {
                "server": "35.208.59.201:50002:s",  # Frencoin ElectrumX server (SSL)
                "electrum_path": wallet_dir,
                "auto_connect": False,
                "oneserver": True,
                "timeout": 30,
                "rpc": False,
            }
        )

        self.network = Network(self.config)
        self.network.start()

        self.main_screen.status = "Resolving & connecting…"

        # Initial status probe
        self._update_network_status()

        if os.path.exists(wallet_path):
            try:
                storage = WalletStorage(wallet_path)
                
                # Check if wallet is encrypted - if so, we need password before loading
                if storage.is_encrypted():
                    # Store storage reference and prompt for password
                    self._pending_encrypted_storage = storage
                    self._pending_wallet_path = wallet_path
                    # Schedule password prompt on next frame
                    Clock.schedule_once(lambda dt: self._prompt_for_wallet_password(), 0.1)
                    return
                
                # Unencrypted wallet - load directly
                self._load_wallet_from_storage(storage, wallet_path)
            except WalletFileException as e:
                # Corrupt/unknown wallet type — back it up and force restore flow
                try:
                    backup_path = wallet_path + ".corrupt"
                    os.replace(wallet_path, backup_path)
                except Exception:
                    pass
                self.wallet = None
                self.seed_quiz_done = False
                self.main_screen.quiz_completed = False
                self._error(
                    f"Wallet file error. Please restore or create a new wallet."
                )
                RestoreWalletPopup().open()
                return
            except Exception as e:
                # Catch ANY other exception to prevent silent failures
                self.wallet = None
                self.seed_quiz_done = False
                self.main_screen.quiz_completed = False
                self._error(
                    f"Error loading wallet. Please restore or create a new wallet."
                )
                RestoreWalletPopup().open()
                return
        else:
            # First run: prompt to restore or create
            self.seed_quiz_done = False
            if self.config:
                try:
                    self.config.set_key("seed_quiz_done", False)
                except Exception:
                    pass
            self.main_screen.quiz_completed = False
            RestoreWalletPopup().open()

        self.refresh_wallet()

    def _prompt_for_wallet_password(self):
        """Show password prompt for encrypted wallet."""
        from electrum.util import InvalidPassword
        
        # Check if we still need to prompt (wallet may have loaded already)
        if not self._pending_encrypted_storage or not self._pending_wallet_path:
            return
        
        # Check cooldown first - but don't auto-retry, let user dismiss error and try again
        remaining = self._get_password_cooldown_seconds()
        if remaining > 0:
            minutes = remaining // 60
            seconds = remaining % 60
            if minutes > 0:
                time_str = f"{minutes}m {seconds}s"
            else:
                time_str = f"{seconds}s"
            
            def on_cooldown_dismiss():
                # Re-prompt after user dismisses cooldown message
                Clock.schedule_once(lambda dt: self._prompt_for_wallet_password(), 0.3)
            
            self._error_with_image_and_callback(
                f"Too many failed attempts.\nPlease wait {time_str} before trying again.",
                "assets/wrong_password.png",
                on_cooldown_dismiss
            )
            return
        
        def on_password_entered(password):
            storage = self._pending_encrypted_storage
            wallet_path = self._pending_wallet_path
            
            if not storage or not wallet_path:
                self._error("Wallet loading error. Please restart the app.")
                return
            
            try:
                # Try to decrypt with the provided password
                storage.decrypt(password)
                
                # Success! Reset failed attempts
                self._reset_password_attempts()
                
                # Clear pending references
                self._pending_encrypted_storage = None
                self._pending_wallet_path = None
                
                # Now load the wallet
                self._load_wallet_from_storage(storage, wallet_path)
                
            except InvalidPassword:
                self._record_failed_password()
                remaining = self._get_password_cooldown_seconds()
                
                def reprompt_after_dismiss():
                    # Only re-prompt if wallet still needs to be loaded
                    if self._pending_encrypted_storage and self._pending_wallet_path:
                        Clock.schedule_once(lambda dt: self._prompt_for_wallet_password(), 0.1)
                
                if remaining > 0:
                    minutes = remaining // 60
                    seconds = remaining % 60
                    if minutes > 0:
                        time_str = f"{minutes}m {seconds}s"
                    else:
                        time_str = f"{seconds}s"
                    self._error_with_image_and_callback(
                        f"Wrong password.\nToo many failed attempts. Please wait {time_str}.",
                        "assets/wrong_password.png",
                        reprompt_after_dismiss
                    )
                else:
                    self._error_with_image_and_callback(
                        "Wrong password.", 
                        "assets/wrong_password.png",
                        reprompt_after_dismiss
                    )
            except Exception:
                self._error("Error decrypting wallet.")
        
        EnterPasswordPopup(submit_cb=on_password_entered).open()

    def _load_wallet_from_storage(self, storage, wallet_path):
        """Load wallet from storage object (must be decrypted if encrypted)."""
        try:
            # CRITICAL: Pass storage to WalletDB so save_db() works correctly
            db = WalletDB(storage.read(), storage=storage, manual_upgrades=False)
            
            self.wallet = Wallet(db, config=self.config)
            # Store reference to storage for saving (belt and suspenders)
            self.wallet.storage = storage
            self.wallet.start_network(self.network)

            # Restore quiz state
            self.seed_quiz_done = bool(self.config.get("seed_quiz_done", False))
            self.main_screen.quiz_completed = self.seed_quiz_done

            # Restore saved display address from wallet DB
            saved_addr = self.wallet.db.get("current_display_address", None)
            if saved_addr and saved_addr in self.wallet.get_receiving_addresses():
                self._current_display_address = saved_addr
                # Ensure current address is in displayed_addresses list
                try:
                    displayed = self.wallet.db.get("displayed_addresses", [])
                    if saved_addr not in displayed:
                        displayed.append(saved_addr)
                        self.wallet.db.put("displayed_addresses", displayed)
                        self.wallet.save_db()
                except Exception:
                    pass

            # If seed quiz wasn't completed, resume it
            if not self.seed_quiz_done:
                try:
                    seed = self.wallet.get_seed(None)
                    if seed:
                        # Schedule seed view popup after UI is ready
                        Clock.schedule_once(
                            lambda dt: self.open_seed_backup_flow(seed), 0.5
                        )
                except Exception:
                    # Wallet might be encrypted or restored from xpub
                    pass
            
            self.refresh_wallet()
            
        except WalletFileException:
            raise
        except Exception:
            raise

    def _create_new_wallet(self):
        wallet_dir = self._get_wallet_dir()
        os.makedirs(wallet_dir, exist_ok=True)
        set_secure_dir_permissions(wallet_dir)
        wallet_path = os.path.join(wallet_dir, "default_wallet")
        assert self.config is not None
        result = create_new_wallet(
            path=wallet_path,
            config=self.config,
            seed_type="standard",
            gap_limit=None,
            encrypt_file=False,
        )
        self.wallet = result["wallet"]
        seed = result["seed"]

        # create_new_wallet already sets up storage properly on db
        # Just copy the reference to wallet.storage for convenience
        if hasattr(self.wallet.db, 'storage') and self.wallet.db.storage is not None:
            self.wallet.storage = self.wallet.db.storage
        else:
            # Fallback: only create new storage if db doesn't have one (shouldn't happen)
            storage = WalletStorage(wallet_path)
            self.wallet.db.storage = storage
            self.wallet.storage = storage
            
        # Verify wallet_type was set correctly
        wallet_type = self.wallet.db.get('wallet_type')
        if wallet_type is None:
            self.wallet.db.put('wallet_type', 'standard')

        # Force save to ensure data is on disk
        self.wallet.db.set_modified(True)
        try:
            self.wallet.save_db()
            set_secure_file_permissions(wallet_path)
        except Exception:
            pass

        self.wallet.start_network(self.network)

        self.seed_quiz_done = False
        if self.config:
            try:
                self.config.set_key("seed_quiz_done", False)
            except Exception:
                pass
        self.main_screen.quiz_completed = False
        self.open_seed_backup_flow(seed)
        self.refresh_wallet()

    def _restore_wallet_from_seed(self, seed_text: str):
        # Restore wallet from a 12-word seed and skip the quiz
        wallet_dir = self._get_wallet_dir()
        os.makedirs(wallet_dir, exist_ok=True)
        set_secure_dir_permissions(wallet_dir)
        wallet_path = os.path.join(wallet_dir, "default_wallet")
        from electrum.wallet import restore_wallet_from_text

        assert self.config is not None
        d = restore_wallet_from_text(
            seed_text,
            path=wallet_path,
            config=self.config,
            passphrase=None,
            password=None,
            encrypt_file=False,
            gap_limit=None,
        )
        self.wallet = d["wallet"]
        
        # restore_wallet_from_text already sets up storage properly on db
        # Just copy the reference to wallet.storage for convenience
        if hasattr(self.wallet.db, 'storage') and self.wallet.db.storage is not None:
            self.wallet.storage = self.wallet.db.storage
        else:
            # Fallback: only create new storage if db doesn't have one (shouldn't happen)
            storage = WalletStorage(wallet_path)
            self.wallet.db.storage = storage
            self.wallet.storage = storage

        # Verify wallet_type was set correctly
        wallet_type = self.wallet.db.get('wallet_type')
        if wallet_type is None:
            self.wallet.db.put('wallet_type', 'standard')

        # Force save to ensure data is on disk
        self.wallet.db.set_modified(True)
        try:
            self.wallet.save_db()
            set_secure_file_permissions(wallet_path)
        except Exception:
            pass

        self.wallet.start_network(self.network)

        self.seed_quiz_done = True
        if self.config:
            try:
                self.config.set_key("seed_quiz_done", True)
            except Exception:
                pass
        self.main_screen.quiz_completed = True
        self._pending_wallet_restored_popup = True
        Clock.schedule_once(
            lambda dt: self.open_password_dialog(first_time_setup=True), 0.1
        )
        self.refresh_wallet()

    # ---------- Network status handling ----------

    def _on_network_event(self, *args, **kwargs):
        """
        Called by Electrum when network status changes.
        Runs in Electrum's thread; push to Kivy's main thread.
        We don't rely on the exact args because this fork's trigger_callback
        isn't passing an 'event' param.
        """
        Clock.schedule_once(lambda dt: self._update_network_status(), 0)

    def _update_network_status(self):
        """Use Electrum's own get_status() to drive the status line."""
        if not self.network or not self.main_screen:
            return

        try:
            status_obj = self.network.get_status()
        except Exception:
            self.main_screen.status = "Network status error"
            return

        # Electrum usually returns (state, server)
        server = None
        if isinstance(status_obj, tuple) and status_obj:
            state = status_obj[0]
            if len(status_obj) > 1:
                server = status_obj[1]
        else:
            state = status_obj

        state_str = str(state)

        if state_str == "connected":
            text = "Connected"
            if server:
                text += f" • {server}"
            if self.wallet:
                try:
                    if self.wallet.is_up_to_date():
                        text += " • Synchronized"
                    else:
                        text += " • Syncing…"
                except Exception:
                    pass
            self.main_screen.status = text

        elif state_str == "connecting":
            if server:
                self.main_screen.status = f"Connecting to {server}…"
            else:
                self.main_screen.status = "Connecting…"

        elif state_str == "disconnected":
            self.main_screen.status = (
                "Unable to connect to node. Check server/IP or internet."
            )

        else:
            # Any other string/enum – just show it so you see what Electrum thinks
            self.main_screen.status = f"Network status: {state_str}"

    # ---------- Seed popups ----------

    def open_main_menu(self):
        MenuPopup().open()

    def apply_softinput_below_target(self, focused: bool):
        try:
            if focused:
                if not hasattr(self, "_prev_softinput_mode"):
                    self._prev_softinput_mode = Window.softinput_mode
                try:
                    Window.softinput_mode = "below_target"
                except Exception:
                    Window.softinput_mode = "pan"
            else:
                if hasattr(self, "_prev_softinput_mode"):
                    Window.softinput_mode = self._prev_softinput_mode
                    delattr(self, "_prev_softinput_mode")
        except Exception:
            pass

    def on_pause(self):
        # Save wallet state when app is paused to prevent data loss on crash
        if self.wallet:
            try:
                self.wallet.save_db()
            except Exception:
                pass
        return True

    def on_resume(self):
        # Force canvas redraw to fix black screen issue after pause/resume
        try:
            if self.main_screen:
                self.main_screen.canvas.ask_update()
            # Also try to refresh the root window
            from kivy.core.window import Window

            Window.canvas.ask_update()
        except Exception:
            pass

        # Refresh wallet state when app resumes
        # Use a background thread to avoid ANR when wallet operations are slow
        def _bg_resume():
            # Small delay to let the UI settle after resume
            import time

            time.sleep(0.3)
            # Schedule the actual refresh on the main thread
            Clock.schedule_once(lambda dt: self._safe_refresh_wallet(), 0)

        threading.Thread(target=_bg_resume, daemon=True).start()
        return True

    def on_stop(self):
        # Save wallet state when app is stopped
        if self.wallet:
            try:
                self.wallet.save_db()
            except Exception:
                pass
        try:
            from kivy.core.window import Window as _W

            _W.release_all_keyboards()
        except Exception:
            pass
        return True

    def open_fee_settings(self):
        if self.config:
            try:
                val = float(self.config.get("default_fee_fren_kb", 0.014))
            except Exception:
                val = 0.014
        else:
            val = 0.014
        default_feerate = max(0.01, min(0.2, val))
        subtract = (
            bool(self.config.get("subtract_fee", False)) if self.config else False
        )
        skip_confirm = (
            bool(self.config.get("skip_send_confirm", False)) if self.config else False
        )
        FeeSettingsPopup(
            default_feerate=default_feerate,
            subtract_fee=subtract,
            skip_confirm=skip_confirm,
        ).open()

    def open_address_list(self):
        AddressListPopup().open()

    def refresh_and_sync(self):
        if self.main_screen:
            self.main_screen.status = "Refreshing…"

        def _bg():
            try:
                if self.wallet:
                    # run synchronize in background; it can take seconds
                    self.wallet.synchronize()
            except Exception:
                pass
            finally:
                Clock.schedule_once(lambda dt: self.refresh_wallet(), 0)

        threading.Thread(target=_bg, daemon=True).start()

    def _proceed_after_confirm(
        self, feerate: float, subtract: bool, dont_show_again: bool
    ):
        if self.config and dont_show_again:
            try:
                self.config.set_key("skip_send_confirm", True)
            except Exception:
                pass
        if self.config:
            try:
                self.config.set_key("subtract_fee", subtract)
                self.config.set_key("default_feerate_sat_vb", feerate)
            except Exception:
                pass
        self._pending_feerate = feerate
        self._pending_subtract = subtract

        # If the wallet has a password, prompt for it before signing.
        try:
            requires_pw = bool(self.wallet.has_password())
        except Exception:
            requires_pw = False

        if requires_pw:
            EnterPasswordPopup(
                submit_cb=lambda pw: self._finish_send_with_password(pw)
            ).open()
            return

        params = getattr(self, "_pending_send", None)
        if not params:
            return
        dest_addr, amount = params
        self._build_and_broadcast_tx(
            dest_addr,
            amount,
            password=None,
            fren_per_kb=feerate,
            subtract_fee=subtract,
        )

    def open_password_dialog(self, first_time_setup=False):
        SetPasswordPopup(first_time_setup=first_time_setup).open()

    def open_transaction_in_explorer(self, txid: str):
        if not txid:
            return
        try:
            import webbrowser

            webbrowser.open(f"https://explorer.frencoin.org/tx/{txid}")
        except Exception as e:
            self._error(f"Could not open explorer: {e}")

    def _fetch_tx_timestamp_from_explorer(self, txid: str) -> Optional[int]:
        """
        Fetch transaction timestamp from explorer.frencoin.org API.
        Returns unix timestamp or None if fetch fails.
        Results are cached to avoid repeated API calls.
        """
        if not txid:
            return None

        # Check cache first
        if txid in FrencoinApp._tx_timestamp_cache:
            return FrencoinApp._tx_timestamp_cache[txid]

        try:
            import urllib.request
            import json
            import ssl

            url = f"https://explorer.frencoin.org/api/getrawtransaction?txid={txid}&decrypt=1"

            cafile = certifi.where()
            ctx = ssl.create_default_context(cafile=cafile)

            req = urllib.request.Request(
                url, headers={"User-Agent": "Frencoin-Wallet/1.0"}
            )
            with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
                data = json.loads(response.read().decode())
                timestamp = data.get("time")
                if timestamp and isinstance(timestamp, int):
                    FrencoinApp._tx_timestamp_cache[txid] = timestamp
                    return timestamp
        except Exception:
            pass
        return None

    def _finish_send_with_password(self, password: Optional[str]):
        # Check cooldown before attempting
        if self._check_password_cooldown():
            return

        # If wallet has password but none provided, treat as wrong password
        if self.wallet.has_password() and not password:
            self._record_failed_password()
            remaining = self._get_password_cooldown_seconds()
            if remaining > 0:
                minutes = remaining // 60
                seconds = remaining % 60
                if minutes > 0:
                    time_str = f"{minutes}m {seconds}s"
                else:
                    time_str = f"{seconds}s"
                self._error_with_image(
                    f"Wrong password.\nToo many failed attempts. Please wait {time_str}.",
                    "assets/wrong_password.png",
                )
            else:
                self._error_with_image("Wrong password.", "assets/wrong_password.png")
            return

        params = getattr(self, "_pending_send", None)
        self._pending_send = None
        if not params:
            return
        dest_addr, amount = params
        feerate = getattr(self, "_pending_feerate", 0.014)
        subtract = getattr(self, "_pending_subtract", False)
        self._build_and_broadcast_tx(
            dest_addr, amount, password, fren_per_kb=feerate, subtract_fee=subtract
        )

    def _build_and_broadcast_tx(
        self,
        dest_addr: str,
        amount: Decimal,
        password: Optional[str],
        fren_per_kb: float = 0.014,
        subtract_fee: bool = False,
    ):
        if not self.wallet:
            self._error("Wallet not ready yet.")
            return

        # Capture references for the background thread
        wallet = self.wallet
        network = self.network
        main_screen = self.main_screen

        # Show a status message
        if main_screen:
            main_screen.status = "Building transaction..."

        def _do_build_and_broadcast():
            try:
                value = int(amount * COIN)
                coins = wallet.get_spendable_coins(None)

                def fee_estimator(size):
                    try:
                        sat_per_vb = int(round((float(fren_per_kb) * COIN) / 1000.0))
                        return int(round(size * sat_per_vb))
                    except Exception:
                        sat_per_vb = int((float(fren_per_kb) * COIN) / 1000.0)
                        return int(size) * sat_per_vb

                # First pass: estimate fee (add-on-top)
                output1 = PartialTxOutput.from_address_and_value(dest_addr, value)
                tx = wallet.make_unsigned_transaction(
                    coins=coins, outputs=[output1], fee=fee_estimator
                )

                if subtract_fee:
                    try:
                        est_fee = int(tx.get_fee() or 0)
                    except Exception:
                        est_fee = 0
                    new_value = max(value - est_fee, 0)
                    output2 = PartialTxOutput.from_address_and_value(
                        dest_addr, new_value
                    )
                    tx = wallet.make_unsigned_transaction(
                        coins=coins, outputs=[output2], fee=fee_estimator
                    )

                def _update_status_signing(dt):
                    if main_screen:
                        main_screen.status = "Signing transaction..."

                Clock.schedule_once(_update_status_signing, 0)
                try:
                    wallet.sign_transaction(tx, password=password)
                finally:
                    # Clear password from memory after use
                    if password:
                        secure_clear_string(password)

                def _update_status_broadcast(dt):
                    if main_screen:
                        main_screen.status = "Broadcasting..."

                Clock.schedule_once(_update_status_broadcast, 0)

                import asyncio

                if not network:
                    Clock.schedule_once(lambda dt: self._error("Network not ready."), 0)
                    return

                fut = asyncio.run_coroutine_threadsafe(
                    network.broadcast_transaction(tx), _ELECTRUM_LOOP
                )
                fut.result(timeout=30)  # Add timeout to prevent infinite hang
                txid = tx.txid()

                def _on_success(dt):
                    # Reset password attempts on successful send
                    self._reset_password_attempts()
                    self._success_with_image(
                        f"Transaction broadcasted!\n\nTXID:\n{txid}",
                        "assets/tx_success.png",
                        copyable_text=txid,
                    )
                    self.refresh_wallet()
                    # Clear send fields
                    if main_screen:
                        main_screen.send_to = ""
                        main_screen.amount = ""

                Clock.schedule_once(_on_success, 0)

            except NotEnoughFunds:
                Clock.schedule_once(lambda dt: self._error("Not enough funds."), 0)
            except Exception as e:
                err_msg = str(e)
                err_str = err_msg.lower()
                if (
                    "password" in err_str
                    or "incorrect" in err_str
                    or "wrong" in err_str
                ):

                    def _handle_password_error(dt):
                        self._record_failed_password()
                        remaining = self._get_password_cooldown_seconds()
                        if remaining > 0:
                            minutes = remaining // 60
                            seconds = remaining % 60
                            if minutes > 0:
                                time_str = f"{minutes}m {seconds}s"
                            else:
                                time_str = f"{seconds}s"
                            self._error_with_image(
                                f"Wrong password.\nToo many failed attempts. Please wait {time_str}.",
                                "assets/wrong_password.png",
                            )
                        else:
                            self._error_with_image(
                                "Wrong password.", "assets/wrong_password.png"
                            )

                    Clock.schedule_once(_handle_password_error, 0)
                else:
                    Clock.schedule_once(
                        lambda dt, msg=err_msg: self._error(f"Error: {msg}"), 0
                    )
            finally:
                Clock.schedule_once(lambda dt: self.refresh_wallet(), 0)

        # Run in background thread to avoid blocking UI
        thread = threading.Thread(target=_do_build_and_broadcast, daemon=True)
        thread.start()

    def _get_password_cooldown_seconds(self) -> int:
        """Get remaining cooldown seconds, or 0 if no cooldown active."""
        import time

        remaining = self._password_cooldown_until - time.time()
        return max(0, int(remaining))

    def _get_cooldown_duration(self) -> int:
        """Get cooldown duration in seconds based on failed attempts."""
        # First 3 attempts: no cooldown
        # 4th attempt: 1 minute
        # 5th attempt: 3 minutes
        # 6th attempt: 5 minutes
        # 7th+: add 5 minutes each time (10, 15, 20, ...)
        attempts = self._failed_password_attempts
        if attempts < 3:
            return 0
        elif attempts == 3:
            return 60  # 1 minute
        elif attempts == 4:
            return 180  # 3 minutes
        else:
            # 5 minutes + 5 minutes for each attempt beyond 5
            return 300 + (attempts - 5) * 300

    def _record_failed_password(self):
        """Record a failed password attempt and set cooldown if needed."""
        import time

        self._failed_password_attempts += 1
        cooldown = self._get_cooldown_duration()
        if cooldown > 0:
            self._password_cooldown_until = time.time() + cooldown
        self._save_security_state()

    def _reset_password_attempts(self):
        """Reset failed attempts on successful password entry."""
        self._failed_password_attempts = 0
        self._password_cooldown_until = 0
        self._save_security_state()

    def _check_password_cooldown(self) -> bool:
        """Check if in cooldown. If so, show error and return True."""
        remaining = self._get_password_cooldown_seconds()
        if remaining > 0:
            minutes = remaining // 60
            seconds = remaining % 60
            if minutes > 0:
                time_str = f"{minutes}m {seconds}s"
            else:
                time_str = f"{seconds}s"
            self._error_with_image(
                f"Too many failed attempts.\nPlease wait {time_str} before trying again.",
                "assets/wrong_password.png",
            )
            return True
        return False

    def set_wallet_password(self, old_pw: str | None, new_pw: str | None):
        if not self.wallet:
            self._error("Wallet not ready yet.")
            return

        # Check cooldown before attempting
        if self._check_password_cooldown():
            return

        # If wallet has password but none provided, treat as wrong password
        if self.wallet.has_password() and not old_pw:
            self._record_failed_password()
            remaining = self._get_password_cooldown_seconds()
            if remaining > 0:
                minutes = remaining // 60
                seconds = remaining % 60
                if minutes > 0:
                    time_str = f"{minutes}m {seconds}s"
                else:
                    time_str = f"{seconds}s"
                self._error_with_image(
                    f"Wrong password.\nToo many failed attempts. Please wait {time_str}.",
                    "assets/wrong_password.png",
                )
            else:
                self._error_with_image("Wrong password.", "assets/wrong_password.png")
            return

        try:
            self.wallet.update_password(old_pw, new_pw, encrypt_storage=bool(new_pw))
            # Success - reset failed attempts
            self._reset_password_attempts()
            # Only show success popup if password was actually set
            if new_pw:
                # Check if we need to show wallet restored popup first
                if getattr(self, "_pending_wallet_restored_popup", False):
                    self._pending_wallet_restored_popup = False
                    self._info_with_image(
                        "Wallet restored from seed.", "assets/wallet_restored.png"
                    )
                else:
                    self._info_with_image(
                        "Password updated.", "assets/password_updated.png"
                    )
            # If no password set, the warning popup already showed - no additional popup needed
        except Exception as e:
            err_str = str(e).lower()
            # Normalize error messages for security - don't reveal if password exists
            if "password" in err_str or "incorrect" in err_str or "wrong" in err_str:
                self._record_failed_password()
                remaining = self._get_password_cooldown_seconds()
                if remaining > 0:
                    minutes = remaining // 60
                    seconds = remaining % 60
                    if minutes > 0:
                        time_str = f"{minutes}m {seconds}s"
                    else:
                        time_str = f"{seconds}s"
                    self._error_with_image(
                        f"Wrong password.\nToo many failed attempts. Please wait {time_str}.",
                        "assets/wrong_password.png",
                    )
                else:
                    self._error_with_image(
                        "Wrong password.", "assets/wrong_password.png"
                    )
            else:
                self._error(f"Could not update password: {e}")

    def remove_wallet_password(self, old_pw: str | None):
        self.set_wallet_password(old_pw, None)

    def _show_seed_with_password(self, password: Optional[str]):
        # Check cooldown before attempting
        if self._check_password_cooldown():
            return

        # If wallet has password but none provided, treat as wrong password
        if self.wallet.has_password() and not password:
            self._record_failed_password()
            remaining = self._get_password_cooldown_seconds()
            if remaining > 0:
                minutes = remaining // 60
                seconds = remaining % 60
                if minutes > 0:
                    time_str = f"{minutes}m {seconds}s"
                else:
                    time_str = f"{seconds}s"
                self._error_with_image(
                    f"Wrong password.\nToo many failed attempts. Please wait {time_str}.",
                    "assets/wrong_password.png",
                )
            else:
                self._error_with_image("Wrong password.", "assets/wrong_password.png")
            return

        error_occurred = None
        try:
            seed = self.wallet.get_seed(password)
            # Success - reset failed attempts
            self._reset_password_attempts()
            SeedViewFromMenuPopup(full_seed=seed).open()
        except Exception as e:
            error_occurred = e
        finally:
            # Clear password from memory after use
            if password:
                secure_clear_string(password)

        if error_occurred:
            err_str = str(error_occurred).lower()
            if "password" in err_str or "incorrect" in err_str or "wrong" in err_str:
                self._record_failed_password()
                remaining = self._get_password_cooldown_seconds()
                if remaining > 0:
                    minutes = remaining // 60
                    seconds = remaining % 60
                    if minutes > 0:
                        time_str = f"{minutes}m {seconds}s"
                    else:
                        time_str = f"{seconds}s"
                    self._error_with_image(
                        f"Wrong password.\nToo many failed attempts. Please wait {time_str}.",
                        "assets/wrong_password.png",
                    )
                else:
                    self._error_with_image(
                        "Wrong password.", "assets/wrong_password.png"
                    )
            else:
                self._error(f"Cannot access recovery phrase: {error_occurred}")

    def open_seed_backup_flow(self, seed: str):
        self._last_seed_phrase = seed
        SeedViewPopup(full_seed=seed).open()

    def open_seed_quiz(self, seed: str = None):
        if seed is None:
            if self.wallet:
                try:
                    seed = self.wallet.get_seed(None)
                except Exception as e:
                    self._error(f"Cannot access recovery phrase: {e}")
                    return
            elif self._last_seed_phrase:
                seed = self._last_seed_phrase
            else:
                self._error("No recovery phrase available.")
                return

        words = seed.split()
        if len(words) < 12:
            self._error("Seed phrase is unexpected length.")
            return

        missing_indices = sorted(secrets.SystemRandom().sample(range(len(words)), 3))
        masked_display = format_masked_seed(seed, missing_indices)

        popup = SeedQuizPopup(
            full_seed=seed,
            display_seed=masked_display,
            missing_indices=missing_indices,
        )
        popup.open()

    def open_view_seed_from_menu(self):
        if not self.wallet:
            self._error("Wallet not ready yet.")
            return
        try:
            if self.wallet.has_password():
                EnterPasswordPopup(
                    submit_cb=lambda pw: self._show_seed_with_password(pw)
                ).open()
                return
            seed = self.wallet.get_seed(None)
        except Exception as e:
            self._error(f"Cannot access recovery phrase: {e}")
            return
        SeedViewFromMenuPopup(full_seed=seed).open()

    def on_seed_quiz_completed(self):
        self.seed_quiz_done = True
        self.main_screen.quiz_completed = True
        if self.config:
            try:
                self.config.set_key("seed_quiz_done", True)
            except Exception:
                pass
        # Securely clear seed phrase from memory
        if self._last_seed_phrase:
            secure_clear_string(self._last_seed_phrase)
        self._last_seed_phrase = None
        Clock.schedule_once(
            lambda dt: self.open_password_dialog(first_time_setup=True), 0.1
        )

    # ---------- Utility popups ----------

    def _popup(self, title, text, copyable_text=None):
        """Show a popup with wrapped text. If copyable_text provided, adds Copy button."""
        from kivy.uix.scrollview import ScrollView

        # Main container
        container = BoxLayout(orientation="vertical", spacing=dp(10))

        # Create a label that wraps text properly
        label = Label(
            text=text,
            halign="left",
            valign="top",
            text_size=(None, None),
            size_hint_y=None,
        )
        label.bind(
            width=lambda inst, val: setattr(inst, "text_size", (val - dp(20), None))
        )
        label.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1]))

        scroll = ScrollView(do_scroll_x=False, do_scroll_y=True, size_hint_y=1)
        scroll.add_widget(label)
        container.add_widget(scroll)

        # Button row
        btn_box = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))

        popup = Popup(
            title=title,
            content=container,
            size_hint=(0.95, 0.5),
        )

        if copyable_text:
            copy_btn = Button(text="Copy")

            def do_copy(_inst):
                clipboard_copy_with_timeout(copyable_text, timeout_seconds=60)
                _inst.text = "Copied!"
                Clock.schedule_once(lambda dt: setattr(_inst, "text", "Copy"), 1.5)

            copy_btn.bind(on_release=do_copy)
            btn_box.add_widget(copy_btn)

        close_btn = Button(text="Close")
        close_btn.bind(on_release=popup.dismiss)
        btn_box.add_widget(close_btn)

        container.add_widget(btn_box)
        popup.open()

    def _error(self, msg):
        self._popup("Error", msg)

    def _error_with_image(self, msg, image_path):
        """Show an error popup with a centered image above the message (no title bar)."""
        # Main container
        container = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(15))

        # Image centered at top
        img = Image(
            source=image_path,
            size_hint=(None, None),
            size=(dp(180), dp(180)),
            pos_hint={"center_x": 0.5},
            allow_stretch=True,
            keep_ratio=True,
        )
        container.add_widget(img)

        # Create a label that wraps text properly
        label = Label(
            text=msg,
            halign="center",
            valign="top",
            text_size=(None, None),
            size_hint_y=None,
        )
        label.bind(
            width=lambda inst, val: setattr(inst, "text_size", (val - dp(20), None))
        )
        label.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1]))
        container.add_widget(label)

        # Spacer
        container.add_widget(Widget(size_hint_y=1))

        # Close button
        btn_box = BoxLayout(size_hint_y=None, height=dp(44))
        popup = Popup(
            title="",
            separator_height=0,
            content=container,
            size_hint=(0.9, 0.45),
        )
        close_btn = Button(text="Close")
        close_btn.bind(on_release=popup.dismiss)
        btn_box.add_widget(close_btn)
        container.add_widget(btn_box)

        popup.open()

    def _error_with_image_and_callback(self, msg, image_path, on_dismiss_callback):
        """Show an error popup with image that calls a callback when dismissed."""
        # Main container
        container = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(15))

        # Image centered at top
        img = Image(
            source=image_path,
            size_hint=(None, None),
            size=(dp(180), dp(180)),
            pos_hint={"center_x": 0.5},
            allow_stretch=True,
            keep_ratio=True,
        )
        container.add_widget(img)

        # Create a label that wraps text properly
        label = Label(
            text=msg,
            halign="center",
            valign="top",
            text_size=(None, None),
            size_hint_y=None,
        )
        label.bind(
            width=lambda inst, val: setattr(inst, "text_size", (val - dp(20), None))
        )
        label.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1]))
        container.add_widget(label)

        # Spacer
        container.add_widget(Widget(size_hint_y=1))

        # Close button
        btn_box = BoxLayout(size_hint_y=None, height=dp(44))
        popup = Popup(
            title="",
            separator_height=0,
            content=container,
            size_hint=(0.9, 0.45),
        )
        
        def on_close(_inst):
            popup.dismiss()
            if on_dismiss_callback:
                try:
                    on_dismiss_callback()
                except Exception:
                    pass
        
        close_btn = Button(text="Close")
        close_btn.bind(on_release=on_close)
        btn_box.add_widget(close_btn)
        container.add_widget(btn_box)

        popup.open()

    def _info(self, msg):
        self._popup("Info", msg)

    def _info_with_image(self, msg, image_path):
        """Show an info popup with a centered image above the message (no title bar)."""
        # Main container
        container = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(15))

        # Image centered at top
        img = Image(
            source=image_path,
            size_hint=(None, None),
            size=(dp(250), dp(250)),
            pos_hint={"center_x": 0.5},
            allow_stretch=True,
            keep_ratio=True,
        )
        container.add_widget(img)

        # Create a label that wraps text properly
        label = Label(
            text=msg,
            halign="center",
            valign="top",
            text_size=(None, None),
            size_hint_y=None,
        )
        label.bind(
            width=lambda inst, val: setattr(inst, "text_size", (val - dp(20), None))
        )
        label.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1]))
        container.add_widget(label)

        # Spacer
        container.add_widget(Widget(size_hint_y=1))

        # Close button
        btn_box = BoxLayout(size_hint_y=None, height=dp(44))
        popup = Popup(
            title="",
            separator_height=0,
            content=container,
            size_hint=(0.9, 0.45),
        )
        close_btn = Button(text="Close")
        close_btn.bind(on_release=popup.dismiss)
        btn_box.add_widget(close_btn)
        container.add_widget(btn_box)

        popup.open()

    def _success_with_image(self, msg, image_path, copyable_text=None):
        """Show a success popup with text, then centered image below, optional copy button."""
        # Main container
        container = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(15))

        # Create a label that wraps text properly
        label = Label(
            text=msg,
            halign="center",
            valign="top",
            text_size=(None, None),
            size_hint_y=None,
        )
        label.bind(
            width=lambda inst, val: setattr(inst, "text_size", (val - dp(20), None))
        )
        label.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1]))
        container.add_widget(label)

        # Image centered below text
        img = Image(
            source=image_path,
            size_hint=(None, None),
            size=(dp(200), dp(200)),
            pos_hint={"center_x": 0.5},
            allow_stretch=True,
            keep_ratio=True,
        )
        container.add_widget(img)

        # Spacer
        container.add_widget(Widget(size_hint_y=1))

        # Button row
        btn_box = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(10))
        popup = Popup(
            title="",
            separator_height=0,
            content=container,
            size_hint=(0.9, 0.55),
        )

        if copyable_text:
            copy_btn = Button(text="Copy TXID")

            def do_copy(_inst):
                clipboard_copy_with_timeout(copyable_text, timeout_seconds=60)
                _inst.text = "Copied!"
                Clock.schedule_once(lambda dt: setattr(_inst, "text", "Copy TXID"), 1.5)

            copy_btn.bind(on_release=do_copy)
            btn_box.add_widget(copy_btn)

        close_btn = Button(text="Close")
        close_btn.bind(on_release=popup.dismiss)
        btn_box.add_widget(close_btn)
        container.add_widget(btn_box)

        popup.open()

    # ---------- Wallet actions ----------

    def _safe_refresh_wallet(self):
        """
        Refresh wallet with heavy operations in background thread.
        Used by on_resume to avoid ANR.
        """
        if not self.wallet:
            return

        # Update status immediately on main thread
        self._update_network_status()

        # Update address immediately (fast operation)
        if not self._current_display_address:
            try:
                addresses = self.wallet.get_receiving_addresses()
                if addresses:
                    self._current_display_address = addresses[0]
            except Exception:
                pass
        if not self._current_display_address:
            try:
                self._current_display_address = self.wallet.get_receiving_address()
            except Exception:
                pass

        # Persist the current address if we just set it for the first time
        if self._current_display_address:
            try:
                saved_addr = self.wallet.db.get("current_display_address", None)
                if saved_addr != self._current_display_address:
                    self.wallet.db.put("current_display_address", self._current_display_address)
                    # Also add to displayed_addresses list
                    displayed = self.wallet.db.get("displayed_addresses", [])
                    if self._current_display_address not in displayed:
                        displayed.append(self._current_display_address)
                        self.wallet.db.put("displayed_addresses", displayed)
                    self.wallet.save_db()
            except Exception:
                pass

        if self.main_screen:
            self.main_screen.address = self._current_display_address or ""

        # Run slow operations (balance, history) in background
        def _bg_fetch():
            balance_text = None
            tx_rows = []

            # Fetch balance
            try:
                bal = self.wallet.get_balance()
                if isinstance(bal, dict):
                    confirmed = int(bal.get("confirmed", 0) or 0)
                    unconfirmed = int(bal.get("unconfirmed", 0) or 0)
                else:
                    c, u, *_ = bal
                    confirmed = int(c or 0)
                    unconfirmed = int(u or 0)
                total = confirmed + unconfirmed
                amount = Decimal(int(total)) / COIN
                balance_text = f"{amount:.8f} FREN"
            except Exception as e:
                balance_text = f"Error: {e}"

            # Fetch transaction history
            try:
                history = self.wallet.get_full_history()
                if isinstance(history, dict):
                    items = list(history.values())

                    for item in items[-10:][::-1]:
                        value_obj = item.get("balance_delta") or item.get("value", 0)
                        if hasattr(value_obj, "value"):
                            v_int = int(value_obj.value)
                        else:
                            try:
                                v_int = int(value_obj)
                            except Exception:
                                v_int = 0

                        try:
                            amount_dec = Decimal(v_int) / COIN
                            amount_str = format_amount_6chars(amount_dec)
                        except Exception:
                            amount_str = str(v_int)[:6]
                        direction = "IN" if v_int > 0 else ("OUT" if v_int < 0 else "")

                        txid = item.get("txid", "")
                        ts = (
                            item.get("timestamp")
                            or item.get("date")
                            or item.get("time")
                        )

                        # First check cache before anything else
                        cached_ts = FrencoinApp._tx_timestamp_cache.get(txid)

                        if isinstance(ts, (int, float)) and ts > 0:
                            date_full = datetime.fromtimestamp(int(ts)).strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                        elif cached_ts:
                            # Use cached timestamp from previous explorer fetch
                            date_full = datetime.fromtimestamp(int(cached_ts)).strftime(
                                "%Y-%m-%d %H:%M:%S"
                            )
                        else:
                            # Fallback: fetch timestamp from block explorer using txid
                            explorer_ts = self._fetch_tx_timestamp_from_explorer(txid)
                            if explorer_ts:
                                date_full = datetime.fromtimestamp(
                                    int(explorer_ts)
                                ).strftime("%Y-%m-%d %H:%M:%S")
                            else:
                                date_full = "Loading..."

                        tx_rows.append(
                            {
                                "date": date_full[:10] if date_full else "",
                                "full_date": date_full,
                                "txid": txid,
                                "direction": direction,
                                "amount": amount_str,
                            }
                        )
            except Exception:
                pass

            # Update UI on main thread
            def _update_ui(dt):
                if self.main_screen:
                    if balance_text:
                        self.main_screen.balance = balance_text
                    try:
                        self.main_screen.update_transactions(tx_rows)
                    except Exception:
                        pass

            Clock.schedule_once(_update_ui, 0)

        threading.Thread(target=_bg_fetch, daemon=True).start()

    def refresh_wallet(self):
        # Keep the status line roughly in sync
        self._update_network_status()

        if not self.wallet:
            return

        # Receiving address - use stable "primary" address that doesn't auto-rotate
        # Only set the display address if we don't have one yet
        if not self._current_display_address:
            try:
                # Use the first receiving address as the stable primary address
                addresses = self.wallet.get_receiving_addresses()
                if addresses:
                    self._current_display_address = addresses[0]
            except Exception:
                pass

        # Fall back to get_receiving_address if we still don't have one
        if not self._current_display_address:
            try:
                self._current_display_address = self.wallet.get_receiving_address()
            except Exception:
                pass

        # Persist the current address if we just set it for the first time
        if self._current_display_address:
            try:
                saved_addr = self.wallet.db.get("current_display_address", None)
                if saved_addr != self._current_display_address:
                    self.wallet.db.put("current_display_address", self._current_display_address)
                    # Also add to displayed_addresses list
                    displayed = self.wallet.db.get("displayed_addresses", [])
                    if self._current_display_address not in displayed:
                        displayed.append(self._current_display_address)
                        self.wallet.db.put("displayed_addresses", displayed)
                    self.wallet.save_db()
            except Exception:
                pass

        self.main_screen.address = self._current_display_address or ""

        # Balance: show last known wallet DB state, even if offline
        try:
            if not self.wallet.is_up_to_date():
                if self.main_screen:
                    self.main_screen.balance = "Loading… (syncing)"
        except Exception:
            pass
        try:
            bal = self.wallet.get_balance()
            if isinstance(bal, dict):
                confirmed = int(bal.get("confirmed", 0) or 0)
                unconfirmed = int(bal.get("unconfirmed", 0) or 0)
            else:
                c, u, *_ = bal
                confirmed = int(c or 0)
                unconfirmed = int(u or 0)
            total = confirmed + unconfirmed
            amount = Decimal(int(total)) / COIN
            if self.main_screen:
                self.main_screen.balance = f"{amount:.8f} FREN"
        except Exception as e:
            if self.main_screen:
                self.main_screen.balance = f"Error: {e}"
        # Recent transaction history (best-effort, UI-only)
        tx_rows = []
        txids_to_fetch = []  # Transactions needing timestamp from explorer
        try:
            history = self.wallet.get_full_history()
        except Exception:
            history = None

        if isinstance(history, dict):
            # Electrum typically returns an OrderedDict; newest entries at the end
            items = list(history.values())
            for item in items[-10:][::-1]:  # up to 10 most recent, newest first
                try:
                    value = item.get("value", 0)
                except Exception:
                    value = 0

                # Format amount
                try:
                    amount_dec = Decimal(value) / COIN
                    amount_str = f"{amount_dec:.4f}"
                except Exception:
                    amount_str = str(value)

                # Direction and amount based on sign
                # Use balance_delta if available (includes fee), otherwise fall back to value
                value_obj = item.get("balance_delta") or item.get("value", 0)
                if hasattr(value_obj, "value"):
                    v_int = int(value_obj.value)
                else:
                    try:
                        v_int = int(value_obj)
                    except Exception:
                        v_int = 0

                try:
                    amount_dec = Decimal(v_int) / COIN
                    amount_str = format_amount_6chars(amount_dec)
                except Exception:
                    amount_str = str(v_int)[:6]
                direction = "IN" if v_int > 0 else ("OUT" if v_int < 0 else "")

                # Date / timestamp (best-effort)
                # Try multiple sources for timestamp
                txid = item.get("txid", "")
                ts = item.get("timestamp") or item.get("date") or item.get("time")

                # First check cache for explorer-fetched timestamp
                cached_ts = FrencoinApp._tx_timestamp_cache.get(txid)

                if isinstance(ts, (int, float)) and ts > 0:
                    date_full = datetime.fromtimestamp(int(ts)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                elif cached_ts:
                    # Use cached timestamp from explorer
                    date_full = datetime.fromtimestamp(int(cached_ts)).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                else:
                    date_full = "Loading..."
                    # Queue this txid for background fetch if not already cached
                    if txid and txid not in FrencoinApp._tx_timestamp_cache:
                        txids_to_fetch.append(txid)

                tx_rows.append(
                    {
                        "date": date_full[:10] if date_full else "",
                        "full_date": date_full,
                        "txid": txid,
                        "direction": direction,
                        "amount": amount_str,
                    }
                )

        try:
            self.main_screen.update_transactions(tx_rows)
        except Exception:
            # Never let a history parsing issue break the main UI
            pass

        # If there are transactions without timestamps, fetch them in background
        if txids_to_fetch:

            def _fetch_timestamps_bg():
                for txid in txids_to_fetch:
                    self._fetch_tx_timestamp_from_explorer(txid)
                # After fetching, schedule a UI refresh
                Clock.schedule_once(lambda dt: self.refresh_wallet(), 0.1)

            threading.Thread(target=_fetch_timestamps_bg, daemon=True).start()

    def is_connected(self):
        interface = self.interface
        return interface is not None and interface.is_connected_and_ready()

    def _network_state_is_connected(self) -> bool:
        """Helper: ask Electrum if it thinks we are connected."""
        if not self.network:
            return False
        try:
            return bool(self.network.is_connected())
        except Exception:
            return False

    def copy_receive_address(self):
        addr = (self.main_screen.address or "").strip()
        if not addr:
            self._error("No address to copy yet.")
            return
        try:
            clipboard_copy_with_timeout(addr, timeout_seconds=60)
        except Exception as e:
            self._error(f"Could not copy address: {e}")
            return
        # Lightweight feedback in the status line
        self.main_screen.status = "Address copied to clipboard."

    def generate_new_receive_address(self):
        """Generate a new receiving address and set it as the current display address."""
        if not self.wallet:
            self._error("Wallet not ready yet.")
            return

        try:
            # Get the next unused address from the wallet
            # This gets an address that hasn't been used in transactions
            new_addr = self.wallet.get_unused_address()

            # If no unused address available, try to create one beyond gap limit
            if not new_addr or new_addr == self._current_display_address:
                try:
                    new_addr = self.wallet.create_new_address(for_change=False)
                    self.wallet.save_db()
                except Exception:
                    # Fall back to getting any receiving address different from current
                    addresses = self.wallet.get_receiving_addresses()
                    for addr in addresses:
                        if addr != self._current_display_address:
                            if not self.wallet.adb.is_used(addr):
                                new_addr = addr
                                break

            if new_addr and new_addr != self._current_display_address:
                # Save the OLD address to displayed addresses list before switching
                if self._current_display_address:
                    try:
                        displayed = self.wallet.db.get("displayed_addresses", [])
                        if self._current_display_address not in displayed:
                            displayed.append(self._current_display_address)
                            self.wallet.db.put("displayed_addresses", displayed)
                            self.wallet.save_db()
                    except Exception:
                        pass

                self._current_display_address = new_addr
                self.main_screen.address = new_addr
                self.main_screen.status = "New address generated."
                # Save the new address to wallet DB for persistence
                try:
                    self.wallet.db.put("current_display_address", new_addr)
                    self.wallet.save_db()
                except Exception:
                    pass
            else:
                self._error("No new unused address available.")
        except Exception as e:
            self._error(f"Could not generate new address: {e}")

    def send_funds(self, dest_addr: str, amount_str: str):
        if not self.wallet:
            self._error("Wallet not ready yet.")
            return

        if not self.seed_quiz_done:
            self._error("Please finish the recovery phrase quiz before sending.")
            return

        dest_addr = (dest_addr or "").strip()
        if not dest_addr:
            return

        if not is_address(dest_addr):
            self._error("Invalid destination address.")
            return

        try:
            amount = Decimal(amount_str)
        except Exception:
            self._error("Invalid amount.")
            return

        if amount <= 0:
            self._error("Amount must be positive.")
            return

        if not self._network_state_is_connected():
            self._error("Still connecting to the network. Please try again shortly.")
            return

        # If the wallet has a password, prompt for it before signing.
        try:
            requires_pw = bool(self.wallet.has_password())
        except Exception:
            requires_pw = False

        # Confirm send and fee (FREN/kB)
        if self.config:
            try:
                feerate = float(self.config.get("default_fee_fren_kb", 0.014))
            except Exception:
                feerate = 0.014
        else:
            feerate = 0.014
        subtract = (
            bool(self.config.get("subtract_fee", False)) if self.config else False
        )
        # Always set _pending_send with the current transaction details
        self._pending_send = (dest_addr, amount)
        self._pending_feerate = feerate
        self._pending_subtract = subtract
        if not (
            bool(self.config.get("skip_send_confirm", False)) if self.config else False
        ):
            ConfirmSendPopup(default_feerate=feerate, subtract_fee=subtract).open()
            return
        # proceed after confirm or if skipped
        self._proceed_after_confirm(feerate, subtract, dont_show_again=False)


if __name__ == "__main__":
    FrencoinApp().run()
