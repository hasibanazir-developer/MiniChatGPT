"""Backup brain: my own model, fine-tuned on the cleaned DailyDialog data."""

import re

from . import config


class LocalBot:
    """Loads the trained flan-t5 model from the models/ folder and replies."""

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = None

    @property
    def is_available(self):
        """True when the trained model folder exists."""
        return (config.LOCAL_MODEL_DIR / "config.json").exists()

    def _load(self):
        """Load the model only once, the first time it is needed (saves memory)."""
        if self.model is not None:
            return
        if not self.is_available:
            raise RuntimeError(
                f"Trained model not found in {config.LOCAL_MODEL_DIR}. "
                "Unzip minichatgpt-model.zip into that folder."
            )

        # Imported here so the app still starts quickly
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = AutoTokenizer.from_pretrained(config.LOCAL_MODEL_DIR)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(config.LOCAL_MODEL_DIR)
        self.model.to(self.device).eval()

    def reply(self, message):
        """Return one reply. The local model only sees the latest message."""
        self._load()

        import torch

        # Same cleaning + prefix style as the training data
        text = config.LOCAL_PROMPT_PREFIX + message.lower().strip()
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            max_length=config.LOCAL_MAX_INPUT_TOKENS,
            truncation=True,
        ).to(self.device)

        with torch.no_grad():
            output = self.model.generate(
                **inputs,
                max_new_tokens=config.LOCAL_MAX_NEW_TOKENS,
                do_sample=True,
                top_p=0.9,
                temperature=0.8,
                no_repeat_ngram_size=3,
            )

        answer = self.tokenizer.decode(output[0], skip_special_tokens=True).strip()
        # Fix lowercase "i" -> "I" (the training data was all lowercase)
        answer = re.sub(r"\bi\b", "I", answer)
        # Capitalize the first letter of each sentence
        answer = re.sub(r"(^|[.!?]\s+)([a-z])", lambda m: m.group(1) + m.group(2).upper(), answer)
        return answer if answer else "Sorry, I don't know."