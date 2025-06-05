# preference_model/train_reward.py
import torch, os, json, random, pathlib
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForSequenceClassification, TrainingArguments, Trainer

ROOT = pathlib.Path("/opt/lumina/reward")
data_file = ROOT/"pairs.jsonl"
tokenizer  = AutoTokenizer.from_pretrained("thenlper/gte-small")
model      = AutoModelForSequenceClassification.from_pretrained(
                "thenlper/gte-small",
                num_labels=2)

def load_pairs():
    rows = []
    for ln in open(data_file):
        obj = json.loads(ln)
        rows.append({"text": obj["prompt"]+" ## "+obj["choice_a"]+" || "+obj["choice_b"],
                     "label": obj["label"]})
    return Dataset.from_list(rows).train_test_split(test_size=0.1)

ds = load_pairs().map(lambda b: tokenizer(b["text"], truncation=True), batched=True)

trainer = Trainer(
    model=model,
    args=TrainingArguments(
        output_dir=str(ROOT/"ckpt"),
        fp16=True,
        per_device_train_batch_size=16,
        num_train_epochs=1,
        logging_steps=20,
        metric_for_best_model="eval_accuracy",
        evaluation_strategy="epoch"),
    train_dataset=ds["train"],
    eval_dataset=ds["test"],
)

metrics = trainer.train()
print("val_acc", trainer.evaluate()["eval_accuracy"])
trainer.save_model(str(ROOT/"latest")) 