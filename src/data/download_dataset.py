from datasets import load_dataset
from pathlib import Path
import json
import re

# Project folders
PROJECT_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_DIR / "data" / "raw"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"
REPORT_DIR = PROJECT_DIR / "reports"

# Create folders if they do not exist
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# Settings
MAX_WORDS = 25  # skip sentences longer than this


def clean_text(text):
    """Clean one DailyDialog sentence."""
    text = text.lower()
    # Normalize curly quotes
    text = text.replace("’", "'").replace("‘", "'")
    text = text.replace("“", '"').replace("”", '"')
    # Fix "it ' s" -> "it's"
    text = re.sub(r"\s*'\s*", "'", text)
    # Fix "hello ," -> "hello,"
    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    # Remove strange characters
    text = re.sub(r"[^a-z0-9'.,!?;:\s]", " ", text)
    # Add missing space after punctuation: "right.but" -> "right. but"
    text = re.sub(r"([.,!?;:])(?=[a-z])", r"\1 ", text)
    # Remove extra spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


# Download dataset (Parquet version, no loading script needed)
print("Downloading dataset...")
dataset = load_dataset("li2017dailydialog/daily_dialog", revision="refs/convert/parquet", split="train")
print(dataset)

# Build question -> answer pairs from each conversation
records = []
for row in dataset:
    dialog = row["dialog"]
    for i in range(len(dialog) - 1):
        records.append({"question": dialog[i], "answer": dialog[i + 1]})

# Save original conversation pairs
raw_file = RAW_DIR / "dialogue_raw.jsonl"
with raw_file.open("w", encoding="utf-8") as file:
    for record in records:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")

print("Raw conversation pairs:", len(records))

# Clean text and remove invalid, long, or duplicate pairs
cleaned = []
seen = set()
removed_empty = 0
removed_long = 0
removed_duplicates = 0

for record in records:
    question = clean_text(record["question"])
    answer = clean_text(record["answer"])

    if not question or not answer:
        removed_empty += 1
        continue

    if len(question.split()) > MAX_WORDS or len(answer.split()) > MAX_WORDS:
        removed_long += 1
        continue

    key = (question, answer)
    if key in seen:
        removed_duplicates += 1
        continue

    seen.add(key)
    cleaned.append({"question": question, "answer": answer})

# Save cleaned dataset
clean_file = PROCESSED_DIR / "dialogue_cleaned.jsonl"
with clean_file.open("w", encoding="utf-8") as file:
    for record in cleaned:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")

# Save cleaning report
report = {
    "raw_pairs": len(records),
    "clean_pairs": len(cleaned),
    "empty_pairs_removed": removed_empty,
    "long_pairs_removed": removed_long,
    "duplicate_pairs_removed": removed_duplicates,
    "max_words": MAX_WORDS,
}

report_file = REPORT_DIR / "cleaning_report.json"
report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")

print("\nCleaning complete!")
print(json.dumps(report, indent=2))

# Show a few examples so you can check the cleaning
print("\nSample cleaned pairs:")
for record in cleaned[:5]:
    print("Q:", record["question"])
    print("A:", record["answer"])
    print("-" * 40)

print("\nCleaned dataset:", clean_file)
print("Report:", report_file)