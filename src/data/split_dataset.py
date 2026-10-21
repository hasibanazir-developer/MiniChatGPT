
import json
import random
from pathlib import Path

# Project folders
PROJECT_DIR = Path(__file__).resolve().parents[2]
DATASET_FILE = PROJECT_DIR / "data" / "processed" / "dialogue_cleaned.jsonl"
OUTPUT_DIR = PROJECT_DIR / "data" / "processed"

# Make results reproducible
random.seed(42)

# Load cleaned dialogue pairs
records = []

with DATASET_FILE.open("r", encoding="utf-8") as file:
    for line in file:
        records.append(json.loads(line))

# Shuffle records before splitting
random.shuffle(records)

# Split into 90% training and 10% testing
split_index = int(len(records) * 0.9)
train_data = records[:split_index]
test_data = records[split_index:]

# Save training data
train_file = OUTPUT_DIR / "train.jsonl"
with train_file.open("w", encoding="utf-8") as file:
    for record in train_data:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")

# Save testing data
test_file = OUTPUT_DIR / "test.jsonl"
with test_file.open("w", encoding="utf-8") as file:
    for record in test_data:
        file.write(json.dumps(record, ensure_ascii=False) + "\n")

# Display results
print("Dataset split completed!")
print("Total records:", len(records))
print("Training records:", len(train_data))
print("Testing records:", len(test_data))
print("Training file:", train_file)
print("Testing file:", test_file)
