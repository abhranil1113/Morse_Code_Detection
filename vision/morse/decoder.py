import json
from pathlib import Path
from typing import Optional


class MorseDecoder:
    """Decodes Morse code buffers into alphanumeric characters and words."""

    MORSE_TABLE = {
        ".-": "A", "-...": "B", "-.-.": "C", "-..": "D", ".": "E",
        "..-.": "F", "--.": "G", "....": "H", "..": "I", ".---": "J",
        "-.-": "K", ".-..": "L", "--": "M", "-.": "N", "---": "O",
        ".--.": "P", "--.-": "Q", ".-.": "R", "...": "S", "-": "T",
        "..-": "U", "...-": "V", ".--": "W", "-..-": "X", "-.--": "Y",
        "--..": "Z", "-----": "0", ".----": "1", "..---": "2", "...--": "3",
        "....-": "4", ".....": "5", "-....": "6", "--...": "7", "---..": "8",
        "----.": "9", ".-.-.-": ".", "--..--": ",", "..--..": "?"
    }

    QUICK_MACROS = {
        "...---...": "SOS",
        ".... . .-.. .--.": "HELP",
        "-.-- . ...": "YES",
        "-. ---": "NO",
        ".-- .- - . .-.": "WATER",
        "-.-. --- -- . / .... . .-. .": "COME HERE"
    }

    def __init__(self, mapping_file: Optional[str] = "database/datasets/manifests/class_mapping.json"):
        if mapping_file and Path(mapping_file).exists():
            try:
                with open(mapping_file, "r") as f:
                    data = json.load(f)
                    self.MORSE_TABLE.update(data.get("morse_alphabet", {}))
                    self.QUICK_MACROS.update(data.get("quick_commands", {}))
            except Exception:
                pass

        self.current_symbol_buffer = ""
        self.current_text = ""

    def add_symbol(self, sym: str):
        if sym in [".", "-"]:
            self.current_symbol_buffer += sym

    def commit_character(self) -> Optional[str]:
        """Translates current dot-dash buffer to character and appends to text."""
        buf = self.current_symbol_buffer.strip()
        if not buf:
            return None

        # Check prosigns / direct macros first (e.g. SOS prosign "...---...")
        if buf in self.QUICK_MACROS:
            word = self.QUICK_MACROS[buf]
            self.current_text = (self.current_text + " " + word).strip()
            self.current_symbol_buffer = ""
            return word

        char = self.MORSE_TABLE.get(buf, "?")
        self.current_text += char
        self.current_symbol_buffer = ""
        return char

    def commit_space(self):
        if self.current_symbol_buffer:
            self.commit_character()
        if self.current_text and not self.current_text.endswith(" "):
            self.current_text += " "

    def backspace(self):
        if self.current_symbol_buffer:
            self.current_symbol_buffer = self.current_symbol_buffer[:-1]
        elif self.current_text:
            self.current_text = self.current_text[:-1]

    def clear_symbol_buffer(self):
        self.current_symbol_buffer = ""

    def clear(self):
        self.current_symbol_buffer = ""
        self.current_text = ""

    def decode_sequence(self, morse_str: str) -> str:
        """
        Decodes a full Morse string where characters are separated by single spaces
        and words are separated by ' / ' or 3+ spaces.
        Supports prosigns (e.g. '...---...' -> 'SOS') and macros.
        """
        morse_str = morse_str.strip()
        if not morse_str:
            return ""

        # Check direct macro match first
        if morse_str in self.QUICK_MACROS:
            return self.QUICK_MACROS[morse_str]

        # Standardize word separators
        normalized = morse_str.replace("   ", " / ")
        word_tokens = [w.strip() for w in normalized.split(" / ") if w.strip()]
        decoded_words = []

        for word in word_tokens:
            if word in self.QUICK_MACROS:
                decoded_words.append(self.QUICK_MACROS[word])
                continue

            char_tokens = [c.strip() for c in word.split(" ") if c.strip()]
            chars = []
            for c in char_tokens:
                if c in self.QUICK_MACROS:
                    chars.append(self.QUICK_MACROS[c])
                else:
                    chars.append(self.MORSE_TABLE.get(c, "?"))
            decoded_words.append("".join(chars))

        return " ".join(decoded_words)
