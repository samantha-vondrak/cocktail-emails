import json

with open(".changerc", "r") as f:
    changerc_copy = f.read()

with open(".changerc_copy", "w") as f:
    f.write(json.dumps(changerc_copy))