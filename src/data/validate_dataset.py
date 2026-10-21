
import json
from pathlib import Path

# Path to the cleaned dataset
PROJECT_DIR = Path(__file__).resolve().parents[2]
DATASET_FILE = PROJECT_DIR / "data" / "processed" / "dialogue_cleaned.jsonl"

total_rows = 0
empty_rows = 0
long_rows = 0
invalid_rows = 0

# Read and validate each dataset row
with DATASET_FILE.open("r", encoding="utf-8") as file:
    for line in file:
        try:
            record = json.loads(line)

            question = record.get("question", "")
            answer = record.get("answer", "")

            if not question.strip() or not answer.strip():
                empty_rows += 1

            if len(question.split()) > 25 or len(answer.split()) > 25:
                long_rows += 1

            total_rows += 1

        except (json.JSONDecodeError, AttributeError):
            invalid_rows += 1

# Display validation results
print("\nDataset Validation Results")
print("-" * 30)
print("Total rows:", total_rows)
print("Empty pairs:", empty_rows)
print("Pairs exceeding 25 words:", long_rows)
print("Invalid rows:", invalid_rows)

if total_rows > 0 and empty_rows == 0 and long_rows == 0 and invalid_rows == 0:
    print("\nSUCCESS: Dataset is ready for the next stage.")
else:
    print("\nCHECK: Some dataset issues need attention.")
