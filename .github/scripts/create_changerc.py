import os
import json

authors_and_ids = {
    "samantha-vondrak": "V301535",
    "Hasley, Lou": "H331331"
}

author = os.getenv("AUTHOR")
subject = os.getenv("SUBJECT")

print(author)
print(subject)

for key, value in authors_and_ids.items():
    if author in key:
        id = value

changerc = {
    "title": subject,
    "owner": id
}

print(changerc)

with open(".changerc", "w") as f:
    f.write(json.dumps(changerc))
